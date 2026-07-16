#include <stddef.h>  // for size_t, NULL

// Define the structure of a list node
typedef struct s_list {
    void *content;
    struct s_list *next;
} t_list;

// Prototype for the lstdelone function
void ft_lstdelone(t_list *lst, void (*del)(void *));
// Free the content of the node with del, then free the node (do not touch next)
void ft_lstdelone(t_list *lst, void (*del)(void *)) {
    t_list *temp = lst;
    while (temp != NULL) {
        if (del == NULL || temp->content == del) {
            // Free the node with del, then free the node (do not touch next)
            temp->next = NULL;
        }
        temp = temp->next;
    }
}

// Define the lstdelone function prototype
void ft_lstdelone(t_list *lst, void (*del)(void *));
