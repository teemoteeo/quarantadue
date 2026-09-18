/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder_actions.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#             */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

void	coder_do_compile(t_coder *c, t_dongle *left, t_dongle *right)
{
	set_last_compile(c, now_ms());
	log_state(c->sim, c->id, "is compiling");
	ft_usleep(c->sim->time_to_compile);
	dongle_release(left);
	dongle_release(right);
	c->compiles_done++;
}

void	coder_do_debug(t_coder *c)
{
	log_state(c->sim, c->id, "is debugging");
	ft_usleep(c->sim->time_to_debug);
}

void	coder_do_refactor(t_coder *c)
{
	log_state(c->sim, c->id, "is refactoring");
	ft_usleep(c->sim->time_to_refactor);
}
