package com.papermind.backend.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import com.papermind.backend.common.JwtUtil;
import com.papermind.backend.common.UserContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

@Component
public class JwtFilter extends OncePerRequestFilter {

    private static final String HEADER = "Authorization";
    private static final String PREFIX = "Bearer ";
    private static final List<String> WHITELIST = List.of("/api/auth/register", "/api/auth/login");

    private final JwtUtil jwtUtil;
    private final ObjectMapper objectMapper;
    private final boolean enforce;

    public JwtFilter(JwtUtil jwtUtil,
                     ObjectMapper objectMapper,
                     @Value("${app.auth.enforce:false}") boolean enforce) {
        this.jwtUtil = jwtUtil;
        this.objectMapper = objectMapper;
        this.enforce = enforce;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return enforce && WHITELIST.contains(request.getRequestURI());
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        try {
            String header = request.getHeader(HEADER);
            if (header != null && header.startsWith(PREFIX)) {
                long userId = jwtUtil.parseUserId(header.substring(PREFIX.length()));
                UserContext.set(userId);
            } else if (enforce) {
                write401(response);
                return;
            }
            chain.doFilter(request, response);
        } catch (BizException e) {
            write401(response);
        } finally {
            UserContext.clear();
        }
    }

    private void write401(HttpServletResponse response) throws IOException {
        ErrorCode ec = ErrorCode.AUTH_TOKEN_INVALID;
        response.setStatus(ec.getHttpStatus());
        response.setContentType("application/json;charset=UTF-8");
        objectMapper.writeValue(response.getWriter(), ApiResponse.fail(ec.getCode(), ec.getMessage()));
    }
}
