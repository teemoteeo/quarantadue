#include <stddef.h>  // for size_t, NULL

// Define the structure for a list node
typedef struct s_list {
    void *content;  // Pointer to the content of the list node
    struct s_list *next;  // Pointer to the next list node in the list

} t_list;

// Function prototype for adding a new node to the front of the list
void ft_lstadd_front(t_list **lst, t_list *new);  // Add the node new at the beginning of the list
