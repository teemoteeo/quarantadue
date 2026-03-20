This project has been created as partof the 42 curriculum by tcostant

DESCRIPTION

Recreating the printf function

INSTRUCTIONS

Run command "make" and run:

cc -Wall -Wextra -Werror ft_printf.c libftprintf.a

RESOURCES

-man 3 printf
-AI usage: discussed code structure design and approach to eliminate struct usage

After building all the required functions, get_function returns pointer to function needed

ft_handle_format uses get_function to call the function needed and return the number of bytes written

ft_printf itera sulla stringa passata e applica le funzioni
