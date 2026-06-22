/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   state.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/22 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/22 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
 * Coder state and last_compile_start are shared with the monitor thread.
 * All access goes through state_mutex so reads and writes never race.
 */
void	set_last_compile(t_coder *c, long long t)
{
	pthread_mutex_lock(&c->sim->state_mutex);
	c->last_compile_start = t;
	pthread_mutex_unlock(&c->sim->state_mutex);
}

void	set_coder_state(t_coder *c, t_coder_state st)
{
	pthread_mutex_lock(&c->sim->state_mutex);
	c->state = st;
	pthread_mutex_unlock(&c->sim->state_mutex);
}

void	read_coder_state(t_simulation *sim, int i, t_coder_state *st,
			long long *last)
{
	pthread_mutex_lock(&sim->state_mutex);
	*st = sim->coders[i].state;
	*last = sim->coders[i].last_compile_start;
	pthread_mutex_unlock(&sim->state_mutex);
}
