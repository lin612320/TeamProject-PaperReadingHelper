package com.papermind.backend.common;

public enum ErrorCode {

    OK(0, 200, "成功"),
    INVALID_PARAM(1001, 400, "参数缺失或格式错误"),
    FILE_NOT_PDF(1002, 400, "仅支持 PDF 文件"),
    FILE_TOO_LARGE(1003, 400, "文件超过 50MB"),
    PAGE_OUT_OF_RANGE(1004, 400, "页码从 1 开始，超出文档页数"),
    PAPER_NOT_FOUND(2001, 404, "文献不存在"),
    PAPER_NOT_READY(2002, 409, "文献尚未解析完成，暂时无法提问"),
    EMPTY_QUESTION(2003, 422, "问题不能为空"),
    AI_SERVICE_ERROR(3001, 502, "AI 服务调用失败"),
    AI_SERVICE_TIMEOUT(3002, 504, "AI 服务超时（>30s）"),
    STORAGE_ERROR(4001, 500, "文件存储失败"),
    INTERNAL_ERROR(5000, 500, "服务器内部错误");

    private final int code;
    private final int httpStatus;
    private final String message;

    ErrorCode(int code, int httpStatus, String message) {
        this.code = code;
        this.httpStatus = httpStatus;
        this.message = message;
    }

    public int getCode() {
        return code;
    }

    public int getHttpStatus() {
        return httpStatus;
    }

    public String getMessage() {
        return message;
    }
}