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

/* Loop principale del coder: prende entrambi i dongle, poi compila/debugga/
 * refattorizza finché non raggiunge il numero di compile richiesto, e le tre
 * azioni che esegue tenendo i dongle. */

#include "codexion.h"

/*
 * Debug e refactor sono la stessa cosa a meno del messaggio e della durata:
 * il coder annuncia la fase e la attende, senza toccare i dongle.
 */
void	coder_phase(t_coder *c, const char *msg, long long ms)
{
	log_state(c->sim, c->id, msg);
	ft_usleep(ms);
}

/* La compilazione è l'unica fase che rilascia i dongle e conta un giro. */
void	coder_do_compile(t_coder *c, t_dongle *left, t_dongle *right)
{
	set_last_compile(c, now_ms());
	log_state(c->sim, c->id, "is compiling");
	ft_usleep(c->sim->time_to_compile);
	dongle_release(left);
	dongle_release(right);
	c->compiles_done++;
}

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
	coder_phase(c, "is debugging", c->sim->time_to_debug);
	if (check_stop(c->sim))
		return (1);
	coder_phase(c, "is refactoring", c->sim->time_to_refactor);
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
	while (c->compiles_done < c->sim->compiles_required)
	{
		if (coder_cycle(c, left, right))
			return (NULL);
	}
	set_coder_state(c, CODER_DONE);
	return (NULL);
}
