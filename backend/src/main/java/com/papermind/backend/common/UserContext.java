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
        return userId == null ? 1L : userId;
    }

    public static void clear() {
        CURRENT_USER.remove();
    }
}
