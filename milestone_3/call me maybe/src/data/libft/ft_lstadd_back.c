#include <stddef.h>  // for size_t, NULL

// Define the structure for a list node
typedef struct s_list {
    void *content;
    struct s_list *next;  // Pointer to the next list node
} t_list;

// Function prototype for adding a new node at the end of a list
void ft_lstadd_back(t_list **lst, t_list *new);

// Implementation of adding a new node at the end of a list
void ft_lstadd_back(t_list **lst, t_list *new) {
    // Allocate memory for the new node
    new->content = NULL;
    new->next = *lst;

    // Update the list head pointer
    *lst = new;
}
