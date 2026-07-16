#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

typedef struct s_list {
    void *content;
    struct s_list *next;
} t_list;

void ft_lstclear(t_list **lst, void (*del)(void *)) {
    if (!*lst) return;  // list is empty, no need to free anything

    t_list *current = *lst;
    while (current != NULL) {
        if ((*del)(current->content)) {
            // Free the node and set *lst to NULL
            free(current->content);
        }
        current = current->next;
    }

    *lst = NULL;  // free the list
}

// Define the struct at the top of the file as 'typedef struct s_list { void *content; struct s_list *next; } t_list;'
