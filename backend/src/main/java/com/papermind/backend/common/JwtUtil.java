package com.papermind.backend.common;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jws;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;

/**
 * JWT 签发与验签。对齐契约 1.3.0：HS256、有效期 12 小时、过期或篡改一律 6002。
 */
@Component
public class JwtUtil {

    private final SecretKey key;
    private final long ttlHours;

    public JwtUtil(@Value("${app.auth.jwt-secret}") String secret,
                   @Value("${app.auth.token-ttl-hours:12}") long ttlHours) {
        byte[] bytes = secret.getBytes(StandardCharsets.UTF_8);
        if (bytes.length < 32) {
            throw new IllegalStateException(
                "app.auth.jwt-secret 至少需要 32 个字节（HS256 要求 256 位密钥），当前只有 " + bytes.length);
        }
        this.key = Keys.hmacShaKeyFor(bytes);
        this.ttlHours = ttlHours;
    }

    public record Token(String value, Instant expiresAt) {
    }

    public Token issue(long userId, String username) {
        Instant now = Instant.now();
        Instant expiresAt = now.plusSeconds(ttlHours * 3600);
        String token = Jwts.builder()
            .subject(String.valueOf(userId))
            .claim("username", username)
            .issuedAt(Date.from(now))
            .expiration(Date.from(expiresAt))
            .signWith(key)
            .compact();
        return new Token(token, expiresAt);
    }

    public long parseUserId(String token) {
        try {
            Jws<Claims> jws = Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token);
            return Long.parseLong(jws.getPayload().getSubject());
        } catch (JwtException | IllegalArgumentException e) {
            throw new BizException(ErrorCode.AUTH_TOKEN_INVALID);
        }
    }
}
