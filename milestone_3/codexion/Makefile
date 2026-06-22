# **************************************************************************** #
#                                                                              #
#                                                         :::      ::::::::    #
#    Makefile                                           :+:      :+:    :+:    #
#                                                     +:+ +:+         +:+      #
#    By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+         #
#                                                 +#+#+#+#+#+   +#+            #
#    Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              #
#    Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr        #
#                                                                              #
# **************************************************************************** #

NAME		:= codexion
CC			:= cc
CFLAGS		:= -Wall -Wextra -Werror -pthread
RM			:= rm -f

SRCDIR		:= src
INCDIR		:= include
OBJDIR		:= obj

SRCS		:= $(SRCDIR)/main.c \
			   $(SRCDIR)/coder.c \
			   $(SRCDIR)/coder_utils.c \
			   $(SRCDIR)/dongle.c \
			   $(SRCDIR)/scheduler.c \
			   $(SRCDIR)/monitor.c \
			   $(SRCDIR)/logger.c \
			   $(SRCDIR)/heap.c \
			   $(SRCDIR)/simulation.c \
			   $(SRCDIR)/simulation_utils.c \
			   $(SRCDIR)/state.c \
			   $(SRCDIR)/parser.c

OBJS		:= $(SRCS:$(SRCDIR)/%.c=$(OBJDIR)/%.o)
DEPS		:= $(OBJS:.o=.d)

INCLUDES	:= -I$(INCDIR)

all: $(NAME)

$(NAME): $(OBJS)
	$(CC) $(CFLAGS) $(INCLUDES) $(OBJS) -o $(NAME)
	@echo "✅ $(NAME) compiled successfully"

$(OBJDIR)/%.o: $(SRCDIR)/%.c
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $(INCLUDES) -MMD -c $< -o $@

-include $(DEPS)

clean:
	$(RM) -r $(OBJDIR)

fclean: clean
	$(RM) $(NAME)

re: fclean all

.PHONY: all clean fclean re
