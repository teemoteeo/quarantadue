/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder_utils.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+    */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#   #+#             */
/*   Updated: 2026/06/19 00:00:00 by teemoteeo        ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

int	acquire_both_dongles(t_coder *c, t_dongle *left, t_dongle *right)
{
	t_dongle	*dongle1;
	t_dongle	*dongle2;

	if (c->left_dongle <= c->right_dongle)
	{
		dongle1 = left;
		dongle2 = right;
	}
	else
	{
		dongle1 = right;
		dongle2 = left;
	}
	if (scheduler_request_single(c->sim, c->id, dongle1) != 0)
		return (-1);
	if (dongle1 != dongle2
		&& scheduler_request_single(c->sim, c->id, dongle2) != 0)
		return (-1);
	log_msg(c->sim, c->id, "has taken both dongles");
	return (0);
}

int	check_stop(t_simulation *sim)
{
	return (atomic_load(&sim->stop_flag));
}

void	coder_do_compile(t_coder *c, t_dongle *left, t_dongle *right)
{
	c->last_compile_start = now_ms();
	c->state = CODER_COMPILING;
	log_msg(c->sim, c->id, "is compiling");
	ft_usleep(c->sim->time_to_compile);
	dongle_release(left);
	dongle_release(right);
	c->compiles_done++;
}

void	coder_do_debug(t_coder *c)
{
	c->state = CODER_DEBUGGING;
	log_msg(c->sim, c->id, "is debugging");
	ft_usleep(c->sim->time_to_debug);
}

void	coder_do_refactor(t_coder *c)
{
	c->state = CODER_REFACTORING;
	log_msg(c->sim, c->id, "is refactoring");
	ft_usleep(c->sim->time_to_refactor);
}
