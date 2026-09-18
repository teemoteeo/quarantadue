/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+    */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#   #+#             */
/*   Updated: 2026/06/21 00:00:00 by teemoteeo        ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static int	coder_cycle(t_coder *c, t_dongle *left, t_dongle *right)
{
	c->wait_since = now_ms();
	if (acquire_both_dongles(c, left, right) != 0)
		return (1);
	if (check_stop(c->sim))
	{
		dongle_release(left);
		dongle_release(right);
		return (1);
	}
	coder_do_compile(c, left, right);
	if (check_stop(c->sim))
		return (1);
	coder_do_debug(c);
	if (check_stop(c->sim))
		return (1);
	coder_do_refactor(c);
	if (check_stop(c->sim))
		return (1);
	return (0);
}

void	*coder_routine(void *arg)
{
	t_coder		*c;
	t_dongle	*left;
	t_dongle	*right;

	c = (t_coder *)arg;
	left = &c->sim->dongles[c->left_dongle];
	right = &c->sim->dongles[c->right_dongle];
	set_last_compile(c, now_ms());
	while (c->compiles_done < c->sim->compiles_required)
	{
		if (coder_cycle(c, left, right))
			return (NULL);
	}
	set_coder_state(c, CODER_DONE);
	return (NULL);
}
