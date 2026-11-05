package com.papermind.backend.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

/**
 * 后端启动自检：启动完成后打一行日志，说明端口、数据库、Redis、AI 服务是否就绪。
 * AI 服务不通不阻断启动，只在日志里标 down。
 */
@Component
public class StartupChecker {

    private static final Logger log = LoggerFactory.getLogger(StartupChecker.class);

    private final JdbcTemplate jdbcTemplate;
    private final StringRedisTemplate redisTemplate;
    private final RestTemplate restTemplate;

    @Value("${server.port:8080}")
    private String port;

    @Value("${app.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    public StartupChecker(JdbcTemplate jdbcTemplate,
                          StringRedisTemplate redisTemplate,
                          RestTemplate restTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        this.redisTemplate = redisTemplate;
        this.restTemplate = restTemplate;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onStartup() {
        String db = checkDb() ? "ok" : "down";
        String redis = checkRedis() ? "ok" : "down";
        String ai = checkAiService();
        log.info("[STARTUP] port={} db={} redis={} ai-service={}", port, db, redis, ai);
    }

    private boolean checkDb() {
        try {
            jdbcTemplate.queryForObject("SELECT 1", Integer.class);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private boolean checkRedis() {
        try {
            redisTemplate.opsForValue().get("papermind:startup-check");
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    private String checkAiService() {
        try {
            restTemplate.getForEntity(aiServiceUrl + "/internal/health", String.class);
            return "ok";
        } catch (Exception e) {
            return "down(" + e.getClass().getSimpleName() + ")";
        }
    }
}
