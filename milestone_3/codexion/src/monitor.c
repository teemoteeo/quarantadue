/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   monitor.c                                          :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

/* Thread watchdog: controlla il burnout di tutti i coder (fermi troppo a
 * lungo) e, se lo trova (o se hanno finito tutti), alza il flag di stop
 * globale e sveglia chi è in attesa. */

#include "codexion.h"

static int	check_coder_burnout(t_simulation *sim, int i)
{
	long long		now;
	t_coder_state	st;
	long long		last;

	read_coder_state(sim, i, &st, &last);
	if (st == CODER_DONE || st == CODER_BURNED_OUT)
		return (0);
	now = now_ms();
	if (now - last >= sim->time_to_burnout)
	{
		set_coder_state(&sim->coders[i], CODER_BURNED_OUT);
		set_stop(sim);
		log_msg(sim, sim->coders[i].id, "burned out");
		return (2);
	}
	return (1);
}

/*
 * Controlla tutti i coder per burnout. Restituisce:
 * 0 = ancora in esecuzione, 1 = tutti finiti, 2 = burnout rilevato.
 */
static int	check_all_done(t_simulation *sim)
{
	int	i;
	int	rc;
	int	all_done;

	all_done = 1;
	i = 0;
	while (i < sim->nb_coders)
	{
		rc = check_coder_burnout(sim, i);
		if (rc == 2)
			return (2);
		if (rc == 1)
			all_done = 0;
		i++;
	}
	return (all_done);
}

/*
 * Alza il flag di stop globale e sveglia ogni coder bloccato su qualsiasi
 * sched_cond di dongle, così osservano lo stop e si liberano.
 */
static void	signal_stop(t_simulation *sim)
{
	int	i;

	set_stop(sim);
	i = 0;
	while (i < sim->nb_coders)
	{
		pthread_mutex_lock(&sim->dongles[i].sched.mutex);
		pthread_cond_broadcast(&sim->dongles[i].sched.cond);
		pthread_mutex_unlock(&sim->dongles[i].sched.mutex);
		i++;
	}
}

/*
 * Thread monitor: controlla periodicamente tutti i coder per burnout.
 * Se un coder non ha iniziato a compilare entro time_to_burnout ms,
 * registra il burnout e imposta il flag di stop globale.
 */
void	*monitor_routine(void *arg)
{
	t_simulation	*sim;
	int				rc;

	sim = (t_simulation *)arg;
	while (1)
	{
		if (check_stop(sim))
			return (NULL);
		rc = check_all_done(sim);
		if (rc != 0)
		{
			signal_stop(sim);
			return (NULL);
		}
		ft_usleep(1);
	}
	return (NULL);
}
