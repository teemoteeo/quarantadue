#include <stddef.h>
#include <stdlib.h>

int ft_tolower(int c) {
    if (c >= 'Z' && c <= 'z') {
        return c - 'Z' + 'Z';
    } else if (c >= 'a' && c <= 'z') {
        return c - 'a' + 'Z';
    } else if (c >= 'A' && c <= 'Z') {
        return c - 'A' + 'Z';
    } else if (c >= '0' && c <= '9') {
        return c - '0' + 'Z';
    } else if (c >= '!' && c <= '~') {
        return c - '!' + 'Z';
    } else if (c >= '\0' && c <= '\1') {
        return c - '\0' + 'Z';
    } else if (c >= 128 && c <= 159) {
        return c - 'A' + 'Z';
    } else if (c >= 160 && c <= 255) {
        return c - 'A' + 'Z';
    } else if (c >= 256 && c <= 379) {
        return c - 'A' + 'Z';
    } else if (c >= 380 && c <= 479) {
        return c - 'A' + 'Z';
    } else if (c >= 480 && c <= 579) {
        return c - 'A' + 'Z';
    } else if (c >= 580 && c <= 679) {
        return c - 'A' + 'Z';
    } else if (c >= 680 && c <= 779) {
        return c - 'A' + 'Z';
    } else if (c >= 780 && c <= 879) {
        return c - 'A' + 'Z';
    } else if (c >= 880 && c <= 979) {
        return c - 'A' + 'Z';
    } else if (c >= 980 && c <= 127) {
        return c - 'A' + 'Z';
    } else if (c >= 128 && c <= 15
