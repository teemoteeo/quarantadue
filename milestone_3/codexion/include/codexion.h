/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion.h                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#             */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef CODEXION_H
# define CODEXION_H

# include <pthread.h>
# include <sys/time.h>
# include <stdlib.h>
# include <unistd.h>

# define MAX_CODERS		256

typedef enum e_scheduler
{
	CODEX_FIFO,
	CODEX_EDF
}	t_scheduler;

typedef struct s_heap_node
{
	int			coder_id;
	long long	priority;
}	t_heap_node;

typedef enum e_dongle_state
{
	DONGLE_FREE,
	DONGLE_HELD,
	DONGLE_COOLDOWN
}	t_dongle_state;

typedef struct s_simulation	t_simulation;

typedef struct s_sched
{
	pthread_mutex_t	mutex;
	pthread_cond_t	cond;
	t_heap_node		queue[2];
	int				size;
}	t_sched;

typedef struct s_dongle
{
	t_dongle_state	state;
	long long		cooldown_until;
	pthread_mutex_t	mutex;
	t_sched			sched;
	t_simulation	*sim;
}	t_dongle;

typedef enum e_coder_state
{
	CODER_RUNNING,
	CODER_BURNED_OUT,
	CODER_DONE
}	t_coder_state;

typedef struct s_coder
{
	int				id;
	t_coder_state	state;
	int				compiles_done;
	long long		last_compile_start;
	long long		wait_since;
	pthread_t		thread;
	int				left_dongle;
	int				right_dongle;
	t_simulation	*sim;
}	t_coder;

typedef struct s_simulation
{
	int				nb_coders;
	int				time_to_burnout;
	int				time_to_compile;
	int				time_to_debug;
	int				time_to_refactor;
	int				compiles_required;
	int				dongle_cooldown_ms;
	t_scheduler		scheduler_type;

	t_coder			coders[MAX_CODERS];
	t_dongle		dongles[MAX_CODERS];

	int				stop_flag;
	pthread_mutex_t	stop_mutex;

	pthread_mutex_t	log_mutex;
	pthread_mutex_t	state_mutex;

	pthread_t		monitor_thread;
	long long		start_time;
}	t_simulation;

/* parser.c */
int			parse_args(int argc, char **argv, t_simulation *sim);

/* logger.c */
long long	timestamp_ms(const t_simulation *sim);
void		log_msg(t_simulation *sim, int coder_id, const char *msg);
void		log_state(t_simulation *sim, int coder_id, const char *msg);

/* dongle.c */
void		dongle_init(t_dongle *d, t_simulation *sim);
void		dongle_destroy(t_dongle *d);
int			dongle_try_acquire(t_dongle *d);
void		dongle_release(t_dongle *d);
long long	now_ms(void);

/* state.c */
void		set_last_compile(t_coder *c, long long t);
void		set_coder_state(t_coder *c, t_coder_state st);
void		read_coder_state(t_simulation *sim, int i, t_coder_state *st,
				long long *last);

/* coder.c */
void		*coder_routine(void *arg);
int			acquire_both_dongles(t_coder *c, t_dongle *left, t_dongle *right);
int			check_stop(t_simulation *sim);
void		set_stop(t_simulation *sim);

/* coder_utils.c */
void		coder_do_compile(t_coder *c, t_dongle *left, t_dongle *right);
void		coder_do_debug(t_coder *c);
void		coder_do_refactor(t_coder *c);

/* heap.c */
void		heap_init(t_sched *sq);
void		heap_push(t_sched *sq, int coder_id, long long priority);
void		heap_remove_by_id(t_sched *sq, int coder_id);

/* scheduler.c */
int			scheduler_request_single(t_simulation *sim, int coder_id,
				t_dongle *d);

/* monitor.c */
void		*monitor_routine(void *arg);

/* simulation.c */
void		simulation_init(t_simulation *sim);
void		simulation_run(t_simulation *sim);
void		simulation_cleanup(t_simulation *sim);
void		simulation_init_dongles(t_simulation *sim);
void		simulation_init_coders(t_simulation *sim);
void		simulation_spawn_threads(t_simulation *sim);
void		simulation_join_threads(t_simulation *sim);

/* utils */
void		ft_usleep(long long ms);

#endif
