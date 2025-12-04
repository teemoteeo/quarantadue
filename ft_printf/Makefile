# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/11/30 18:54:29 by tcostant          #+#    #+#              #
#    Updated: 2025/12/03 14:52:26 by tcostant         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME = libftprintf.a

CFLAGS = -Wall -Wextra -Werror

CC = cc

SRC = ft_printf.c \
		ft_printf_utils1.c \
		ft_printf_utils2.c \
		ft_putnbr_base.c \
		ft_uitoa.c\
		libft/ft_alloc.c\
		libft/ft_char_1.c\
		libft/ft_char_2.c\
		libft/ft_convert.c\
		libft/ft_join_trim.c\
		libft/ft_lst_clear.c\
		libft/ft_memory_1.c\
		libft/ft_memory_2.c\
		libft/ft_put_fd.c\
		libft/ft_split.c\
		libft/ft_string_1.c\
		libft/ft_string_2.c\
		libft/ft_strmap.c\
		libft/ft_substr.c

OBJ = $(SRC:.c=.o)

all: $(NAME)

$(NAME): $(OBJ)
	ar rcs $(NAME) $(OBJ)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re
