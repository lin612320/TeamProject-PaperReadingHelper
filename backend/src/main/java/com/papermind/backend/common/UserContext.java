package com.papermind.backend.common;

public final class UserContext {

    private static final ThreadLocal<Long> CURRENT_USER = new ThreadLocal<>();

    private UserContext() {
    }

    public static void set(long userId) {
        CURRENT_USER.set(userId);
    }

    public static long currentUserId() {
        Long userId = CURRENT_USER.get();
        if (userId == null) {
            throw new BizException(ErrorCode.AUTH_TOKEN_INVALID);
        }
        return userId;
    }

    public static void clear() {
        CURRENT_USER.remove();
    }
}
