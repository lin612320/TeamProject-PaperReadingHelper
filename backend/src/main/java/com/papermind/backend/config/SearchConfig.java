package com.papermind.backend.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.ThreadPoolExecutor;

/**
 * #76 检索专用线程池。
 * 不复用 AsyncConfig 的 taskExecutor：那个池子跑 PDF 解析（单次 20-40 秒），
 * 检索请求会在它后面排队，等不到线程就直接超时。
 */
@Configuration
public class SearchConfig {

    @Bean(name = "searchExecutor")
    public ThreadPoolTaskExecutor searchExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);    // 常态两个线程：一次请求刚好两个源
        executor.setMaxPoolSize(4);     // 两个请求同时进来时扩到四个
        executor.setQueueCapacity(8);   // 排队上限 8 个任务
        executor.setThreadNamePrefix("search-");
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(10);
        executor.initialize();
        return executor;
    }
}
