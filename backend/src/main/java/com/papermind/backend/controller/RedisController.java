package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/redis")
public class RedisController {

    private final StringRedisTemplate redis;

    public RedisController(StringRedisTemplate redis) {
        this.redis = redis;
    }

    @GetMapping("/ping")
    public ApiResponse<Map<String, Object>> ping() {

        redis.opsForValue().set("papermind:ping", "pong");

        String readBack = redis.opsForValue().get("papermind:ping");

        boolean ok = "pong".equals(readBack);

        Map<String, Object> data = new HashMap<>();
        data.put("written", "pong");
        data.put("readBack", readBack);
        data.put("ok", ok);
        return ApiResponse.ok(data);
    }
}
