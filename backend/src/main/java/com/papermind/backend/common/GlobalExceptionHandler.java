package com.papermind.backend.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(BizException.class)
    public ResponseEntity<ApiResponse<Void>> handleBiz(BizException e) {
        ErrorCode ec = e.getErrorCode();
        return ResponseEntity.status(ec.getHttpStatus())
            .body(ApiResponse.fail(ec.getCode(), ec.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValid(MethodArgumentNotValidException e) {
        ErrorCode ec = ErrorCode.INVALID_PARAM;
        return ResponseEntity.status(ec.getHttpStatus())
            .body(ApiResponse.fail(ec.getCode(), ec.getMessage()));
    }

    // BUG-005：文件超过上限
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ApiResponse<Void>> handleTooLarge(MaxUploadSizeExceededException e) {
        ErrorCode ec = ErrorCode.FILE_TOO_LARGE;
        return ResponseEntity.status(ec.getHttpStatus())
            .body(ApiResponse.fail(ec.getCode(), ec.getMessage()));
    }

    // 路径参数类型不对（例如 /api/papers/abc）
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ApiResponse<Void>> handleTypeMismatch(MethodArgumentTypeMismatchException e) {
        ErrorCode ec = ErrorCode.INVALID_PARAM;
        return ResponseEntity.status(ec.getHttpStatus())
            .body(ApiResponse.fail(ec.getCode(), ec.getMessage()));
    }

    // 请求体不是合法 JSON / 类型不匹配
    @ExceptionHandler(org.springframework.http.converter.HttpMessageNotReadableException.class)
    public ResponseEntity<ApiResponse<Void>> handleBadBody(
            org.springframework.http.converter.HttpMessageNotReadableException e) {
        ErrorCode ec = ErrorCode.INVALID_PARAM;
        return ResponseEntity.status(ec.getHttpStatus())
            .body(ApiResponse.fail(ec.getCode(), ec.getMessage()));
    }

    // 数据库异常，前面怀疑过的「5000 分不清是库挂了还是后端挂了」
    @ExceptionHandler(DataAccessException.class)
    public ResponseEntity<ApiResponse<Void>> handleDb(DataAccessException e) {
        log.error("database error", e);
        ErrorCode ec = ErrorCode.STORAGE_ERROR;
        return ResponseEntity.status(ec.getHttpStatus())
            .body(ApiResponse.fail(ec.getCode(), "数据库访问异常"));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleOther(Exception e) {
        log.error("unexpected error", e);
        ErrorCode ec = ErrorCode.INTERNAL_ERROR;
        return ResponseEntity.status(ec.getHttpStatus())
            .body(ApiResponse.fail(ec.getCode(), ec.getMessage()));
    }
}
