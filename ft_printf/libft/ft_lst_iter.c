/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_lst_iter.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/26 16:58:05 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 12:58:58 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

void	ft_lstiter(t_list *lst, void (*f)(void *))
{
	while (lst)
	{
		f(lst->content);
		lst = lst->next;
	}
}

t_list	*ft_lstmap(t_list *lst, void *(*f)(void *), void (*del)(void *))
{
	t_list	*result;
	t_list	*tmp;

	result = NULL;
	while (lst)
	{
		tmp = ft_lstnew(f(lst->content));
		if (!tmp)
		{
			ft_lstclear(&result, del);
			return (NULL);
		}
		ft_lstadd_back(&result, tmp);
		lst = lst->next;
	}
	return (result);
}

// #include <stdio.h>

// int	main(void)
// {
// 	char	*content1 = "swag";
// 	char	*content2 = "swaaaaag";
// 	char	*content3 = "swaaaaaaaaag";

// 	t_list	*lst = ft_lstnew(content2);
// 	ft_lstadd_front(&lst, ft_lstnew(content1));
// 	ft_lstadd_back(&lst, ft_lstnew(content3));
// 	printf("dimensione lista: %d\n", ft_lstsize(lst));
// 	while (lst)
// 	{
// 		printf("%s\n", (char *)lst->content);
// 		lst = lst->next;
// 	}
// }