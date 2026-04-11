package com.ghost.alpha.utils

import retrofit2.HttpException

fun Throwable.toUserMessage(): String {
    return when (this) {
        is HttpException -> message() ?: "Request failed (${code()})"
        else -> message ?: "Unexpected error"
    }
}