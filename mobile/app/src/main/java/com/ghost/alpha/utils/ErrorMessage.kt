package com.ghost.alpha.utils

import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.io.IOException
import retrofit2.HttpException

fun Throwable.toUserMessage(): String {
    return when (this) {
        is SocketTimeoutException -> "Request timed out. Please check network conditions and retry."
        is UnknownHostException -> "Unable to reach Ghost Alpha servers. Check your internet connection."
        is IOException -> "Network connection failed. Please retry."
        is HttpException -> when (code()) {
            401 -> "Session expired. Please sign in again."
            403 -> "Action blocked by security policy. Complete step-up verification and try again."
            429 -> "Rate limit reached. Please wait a moment before retrying."
            in 500..599 -> "Ghost Alpha services are currently degraded. Please retry shortly."
            else -> message() ?: "Request failed (${code()})"
        }
        else -> message ?: "Unexpected error"
    }
}