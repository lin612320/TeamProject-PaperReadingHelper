package com.papermind.backend.common;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class JwtUtilTest {

    private static final String SECRET = "test-secret-key-must-be-at-least-32-bytes-long";

    @Test
    void issueThenParse() {
        JwtUtil jwt = new JwtUtil(SECRET, 12);
        JwtUtil.Token token = jwt.issue(42L, "liuwanli");
        assertEquals(42L, jwt.parseUserId(token.value()));
    }

    @Test
    void tamperedRejected() {
        JwtUtil jwt = new JwtUtil(SECRET, 12);
        String token = jwt.issue(1L, "a").value();
        String tampered = token.substring(0, token.length() - 2) + "xx";
        assertThrows(BizException.class, () -> jwt.parseUserId(tampered));
    }

    @Test
    void expiredRejected() {
        JwtUtil expired = new JwtUtil(SECRET, -1);
        String token = expired.issue(1L, "a").value();
        assertThrows(BizException.class, () -> new JwtUtil(SECRET, 12).parseUserId(token));
    }
}
