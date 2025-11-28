# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2025/11/24 18:12:53 by tcostant          #+#    #+#              #
#    Updated: 2025/11/28 18:38:53 by tcostant         ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME = libft.a

CC = gcc
CFLAGS = -Wall -Wextra -Werror -g

SRC = ft_alloc.c\
		ft_char_1.c\
		ft_char_2.c\
		ft_convert.c\
		ft_join_trim.c\
		ft_lst_clear.c\
		ft_memory_1.c\
		ft_memory_2.c\
		ft_put_fd.c\
		ft_split.c\
		ft_string_1.c\
		ft_string_2.c\
		ft_strmap.c\
		ft_substr.c\

BONUS_SRC = ft_lst_iter.c\
			ft_lst_new.c\
			ft_lst_utils.c\

OBJ = $(SRC:.c=.o)

BONUS_OBJ = $(BONUS_SRC:.c=.o)

all: $(NAME)

$(NAME): $(OBJ)
	ar rcs $(NAME) $(OBJ)
	@echo "Creato libreria: $(NAME)"

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

bonus: $(OBJ) $(BONUS_OBJ)
	ar rcs $(NAME) $(OBJ) $(BONUS_OBJ)
	@echo "Creato libreria bonus: $(NAME)"
	
clean:
	rm -f $(OBJ) $(BONUS_OBJ)
	@echo "File oggetto rimossi."

fclean: clean
	rm -f $(NAME)
	@echo "Tutto pulito (libreria eliminata)."

re: fclean all