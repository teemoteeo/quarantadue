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

#include "codexion.h"
#include <sys/time.h>

static int	check_coder_burnout(t_simulation *sim, int i)
{
	long long	now;

	if (sim->coders[i].state == CODER_DONE
		|| sim->coders[i].state == CODER_BURNED_OUT)
		return (0);
	now = now_ms();
	if (now - sim->coders[i].last_compile_start
		>= sim->time_to_burnout)
	{
		sim->coders[i].state = CODER_BURNED_OUT;
		log_msg(sim, sim->coders[i].id, "burned out");
		return (2);
	}
	return (1);
}

/*
 * Poll all coders for burnout. Returns:
 * 0 = still running, 1 = all done, 2 = burnout detected.
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

static void	set_stop_and_return(t_simulation *sim)
{
	atomic_store(&sim->stop_flag, 1);
}

/*
 * Monitor thread: polls all coders for burnout.
 * If a coder has not started compiling within time_to_burnout ms,
 * logs burnout and sets the global stop flag.
 */
void	*monitor_routine(void *arg)
{
	t_simulation	*sim;
	int				rc;

	sim = (t_simulation *)arg;
	while (1)
	{
		if (atomic_load(&sim->stop_flag))
			return (NULL);
		rc = check_all_done(sim);
		if (rc != 0)
		{
			set_stop_and_return(sim);
			return (NULL);
		}
		ft_usleep(1);
	}
	return (NULL);
}
