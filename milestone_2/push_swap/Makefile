# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: tcostant <marvin@42.fr>                    +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2026/01/28 14:53:33 by tcostant          #+#    #+#              #
#    Updated: 2026/02/03 18:37:51 by tcostant         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME = push_swap

SRCS = push_swap.c \
       push_swap_utils1.c \
       index.c \
       small_sort.c \
       cost.c \
       turk_sort.c \
       turk_utils.c \
       swap.c \
       push.c \
       rotate.c \
       reverse_rotate.c \
       libft/ft_convert.c \
       libft/ft_isdigit.c


OBJS = $(SRCS:.c=.o)
CC = cc
LIB = push_swap.a

CFLAGS = -Wall -Wextra -Werror

all: $(NAME)

$(NAME): $(OBJS)
	ar rcs $(LIB) $(OBJS)
	$(CC) $(CFLAGS) -o $(NAME) $(LIB)

clean:
	rm -f $(OBJS)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re

