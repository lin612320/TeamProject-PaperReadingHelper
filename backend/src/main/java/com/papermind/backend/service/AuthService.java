package com.papermind.backend.service;

import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import com.papermind.backend.common.JwtUtil;
import com.papermind.backend.dto.AuthDtos;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 注册 / 登录 / 当前用户。对齐契约 1.3.0 与冒烟用例 B06-01~B06-04。
 */
@Service
public class AuthService {

    /** 契约要求 expiresAt 带 Asia/Shanghai 时区语义，输出形如 2026-11-24T22:00:00+08:00 */
    private static final DateTimeFormatter EXPIRES_AT_FMT =
        DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssXXX")
            .withZone(ZoneId.of("Asia/Shanghai"));

    /** 与 PaperController 保持一致的 createdAt 格式（本地时间、无时区后缀） */
    private static final String CREATED_AT_SQL =
        "to_char(created_at AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD\"T\"HH24:MI:SS') AS \"createdAt\" ";

    private final JdbcTemplate jdbcTemplate;
    private final JwtUtil jwtUtil;
    private final PasswordEncoder passwordEncoder;

    /** 账号不存在时也跑一次 bcrypt，让两条失败路径耗时接近，防止按响应时间探测用户名 */
    private final String dummyHash;

    public AuthService(JdbcTemplate jdbcTemplate, JwtUtil jwtUtil, PasswordEncoder passwordEncoder) {
        this.jdbcTemplate = jdbcTemplate;
        this.jwtUtil = jwtUtil;
        this.passwordEncoder = passwordEncoder;
        this.dummyHash = passwordEncoder.encode("papermind-dummy-password");
    }

    public Map<String, Object> register(AuthDtos.RegisterRequest req) {
        String username = req.username().trim();
        String hash = passwordEncoder.encode(req.password());

        Long userId;
        try {
            userId = jdbcTemplate.queryForObject(
                "INSERT INTO users (username, password_hash) VALUES (?, ?) RETURNING id",
                Long.class, username, hash);
        } catch (DuplicateKeyException e) {
            throw new BizException(ErrorCode.AUTH_USERNAME_TAKEN);
        }

        if (userId == null) {
            throw new BizException(ErrorCode.INTERNAL_ERROR);
        }
        return buildAuthToken(userId, username);
    }

    public Map<String, Object> login(AuthDtos.LoginRequest req) {
        String username = req.username().trim();

        UserRow user;
        try {
            user = jdbcTemplate.queryForObject(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (rs, rowNum) -> new UserRow(
                    rs.getLong("id"), rs.getString("username"), rs.getString("password_hash")),
                username);
        } catch (EmptyResultDataAccessException e) {
            passwordEncoder.matches(req.password(), dummyHash);
            throw new BizException(ErrorCode.AUTH_INVALID_CREDENTIALS);
        }

        if (!passwordEncoder.matches(req.password(), user.passwordHash())) {
            throw new BizException(ErrorCode.AUTH_INVALID_CREDENTIALS);
        }
        return buildAuthToken(user.id(), user.username());
    }

    public Map<String, Object> currentUser(long userId) {
        try {
            return jdbcTemplate.queryForObject(
                "SELECT id, username, " + CREATED_AT_SQL + "FROM users WHERE id = ?",
                (rs, rowNum) -> {
                    Map<String, Object> info = new LinkedHashMap<>();
                    info.put("id", rs.getLong("id"));
                    info.put("username", rs.getString("username"));
                    info.put("createdAt", rs.getString("createdAt"));
                    return info;
                },
                userId);
        } catch (EmptyResultDataAccessException e) {
            // 令牌合法但用户已被删：按登录态失效处理
            throw new BizException(ErrorCode.AUTH_TOKEN_INVALID);
        }
    }

    private Map<String, Object> buildAuthToken(long userId, String username) {
        JwtUtil.Token token = jwtUtil.issue(userId, username);

        Map<String, Object> user = new LinkedHashMap<>();
        user.put("id", userId);
        user.put("username", username);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("token", token.value());
        data.put("tokenType", "Bearer");
        data.put("expiresAt", EXPIRES_AT_FMT.format(token.expiresAt()));
        data.put("user", user);
        return data;
    }

    private record UserRow(long id, String username, String passwordHash) {
    }
}
