<script lang="ts">
	import { onMount } from "svelte";
	type Job = {
		title: string;
		company: string;
		location: string;
		mode: string;
		type: string;
		score: number;
		source: string;
		time: string;
		color: string;
		url?: string;
		description?: string;
		telegramMessage?: string;
	};
	let activeNav = $state("Ofertas");
	let search = $state("");
	let filter = $state("Todas");
	let showFilters = $state(false);
	const demoJobs: Job[] = [
		{
			title: "Desarrollador Backend Junior",
			company: "Sofka Technologies",
			location: "Medellín, Colombia",
			mode: "Remoto",
			type: "Tiempo completo",
			score: 94,
			source: "Get on Board",
			time: "Hace 2 h",
			color: "violet",
		},
		{
			title: "Python Developer",
			company: "Endava",
			location: "Bogotá, Colombia",
			mode: "Híbrido",
			type: "Tiempo completo",
			score: 88,
			source: "Job API",
			time: "Hace 4 h",
			color: "blue",
		},
		{
			title: "Software Engineer Backend",
			company: "Rappi",
			location: "Remoto · Colombia",
			mode: "Remoto",
			type: "Tiempo completo",
			score: 83,
			source: "Job API",
			time: "Hace 6 h",
			color: "orange",
		},
		{
			title: "Desarrollador Full Stack",
			company: "Globant",
			location: "Cali, Colombia",
			mode: "Híbrido",
			type: "Contrato",
			score: 79,
			source: "Get on Board",
			time: "Ayer",
			color: "lime",
		},
		{
			title: "Frontend Developer · React",
			company: "BairesDev",
			location: "Remoto",
			mode: "Remoto",
			type: "Tiempo completo",
			score: 75,
			source: "Job API",
			time: "Ayer",
			color: "cyan",
		},
		{
			title: "Programador Web Junior",
			company: "Turing",
			location: "Colombia",
			mode: "Remoto",
			type: "Tiempo completo",
			score: 72,
			source: "Get on Board",
			time: "Hace 2 días",
			color: "rose",
		},
	];
	let jobs = $state<Job[]>(demoJobs);
	let stats = $state({
		found_today: 42,
		compatible: 16,
		sent_today: 8,
		telegram_limit: 10,
		latest_run: null,
	});
	let usingDemo = $state(true);
	let adminToken = $state("");
	let loginUser = $state("");
	let loginPassword = $state("");
	let loginError = $state("");
	let runs = $state<any[]>([]);
	let loadingRuns = $state(false);
	let pipelineRunning = $state(false);
	let pipelineMessage = $state("");
	let latestRun = $state<any>(null);
	let selectedJob = $state<Job | null>(null);
	const navItems = [
		{ label: "Resumen", icon: "grid" },
		{ label: "Ofertas", icon: "search" },
		{ label: "Ejecuciones", icon: "activity" },
		{ label: "Cómo funciona", icon: "info" },
	];
	const filteredJobs = $derived(
		jobs.filter((job) => {
			const matchesSearch = `${job.title} ${job.company} ${job.location}`
				.toLowerCase()
				.includes(search.toLowerCase());
			const matchesFilter =
				filter === "Todas" ||
				job.mode === filter ||
				job.source === filter;
			return matchesSearch && matchesFilter;
		}),
	);

	function scoreTone(score: number) {
		if (score <= 40) return "low";
		if (score <= 69) return "medium";
		if (score <= 95) return "high";
		return "excellent";
	}

	onMount(async () => {
		adminToken = localStorage.getItem("jobhunter_admin_token") || "";
		const apiUrl = (
			import.meta.env.VITE_API_URL || "http://localhost:8000"
		).replace(/\/$/, "");
		try {
			const [jobsResponse, statsResponse] = await Promise.all([
				fetch(`${apiUrl}/api/jobs`),
				fetch(`${apiUrl}/api/stats`),
			]);
			if (!jobsResponse.ok || !statsResponse.ok)
				throw new Error("API unavailable");
			const apiJobs = await jobsResponse.json();
			jobs = apiJobs.map((job: any, index: number) => ({
				title: job.title,
				company: job.company || "Empresa no especificada",
				location: job.location || "Ubicación no especificada",
				mode: job.remote ? "Remoto" : job.location || "Presencial",
				type: "Tiempo completo",
				url: job.url,
				description: job.description,
				telegramMessage: job.telegram_message,
				score: job.match_score ?? job.filter_score ?? 0,
				source: job.source,
				time: job.sent_at
					? "Enviada"
					: job.status === "analyzed"
						? "Analizada"
						: "Pendiente",
				color: ["violet", "blue", "orange", "lime", "cyan", "rose"][
					index % 6
				],
			}));
			stats = await statsResponse.json();
			latestRun = stats.latest_run;
			usingDemo = false;
		} catch {
			// La demo sigue siendo navegable mientras el backend local no está activo.
		}
	});

	onMount(() => {
		const timer = window.setInterval(refreshLiveStatus, 3000);
		return () => window.clearInterval(timer);
	});

	async function refreshLiveStatus() {
		const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
		try {
			const response = await fetch(`${apiUrl}/api/stats`);
			if (!response.ok) return;
			const data = await response.json();
			stats = data;
			latestRun = data.latest_run;
		} catch {
			// El panel conserva el último estado conocido si el backend no responde.
		}
	}

	async function openHistory() {
		activeNav = "Ejecuciones";
		loginError = "";
		if (adminToken) await loadRuns();
	}

	function openHowItWorks() {
		activeNav = "Cómo funciona";
	}

	async function login() {
		loginError = "";
		const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
		try {
			const response = await fetch(`${apiUrl}/api/auth/login`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ username: loginUser, password: loginPassword }),
			});
			if (!response.ok) throw new Error((await response.json()).detail || "No se pudo iniciar sesión");
			const data = await response.json();
			adminToken = data.access_token;
			localStorage.setItem("jobhunter_admin_token", adminToken);
			loginPassword = "";
			await loadRuns();
		} catch (error) {
			loginError = error instanceof Error ? error.message : "No se pudo iniciar sesión";
		}
	}

	async function loadRuns() {
		loadingRuns = true;
		const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
		try {
			const response = await fetch(`${apiUrl}/api/runs`, { headers: { Authorization: `Bearer ${adminToken}` } });
			if (response.status === 401) { logout(); return; }
			if (!response.ok) throw new Error("No se pudo cargar el historial");
			runs = await response.json();
		} catch (error) {
			loginError = error instanceof Error ? error.message : "No se pudo cargar el historial";
		} finally { loadingRuns = false; }
	}

	async function runPipeline() {
		if (!adminToken) {
			openHistory();
			loginError = "Inicia sesión para ejecutar el pipeline.";
			return;
		}
		pipelineRunning = true;
		pipelineMessage = "Iniciando recolección, análisis y envío...";
		const apiUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
		try {
			const response = await fetch(`${apiUrl}/api/pipeline/run`, {
				method: "POST",
				headers: { Authorization: `Bearer ${adminToken}` },
			});
			if (response.status === 401) { logout(); openHistory(); return; }
			if (response.status === 409) throw new Error("Ya hay una ejecución en curso.");
			if (!response.ok) throw new Error("No se pudo iniciar el pipeline.");
			pipelineMessage = "Pipeline en ejecución. Telegram recibirá las mejores ofertas.";
			await watchPipeline();
		} catch (error) {
			pipelineRunning = false;
			pipelineMessage = error instanceof Error ? error.message : "No se pudo iniciar el pipeline.";
		}
	}

	async function watchPipeline() {
		for (let attempt = 0; attempt < 120; attempt += 1) {
			await new Promise((resolve) => setTimeout(resolve, 3000));
			await loadRuns();
			const latest = runs[0];
			if (latest && latest.status !== "running") {
				pipelineRunning = false;
				pipelineMessage = latest.status === "completed" ? `Completado: ${latest.notified_count ?? 0} ofertas enviadas a Telegram.` : "El pipeline terminó con error. Revisa Ejecuciones.";
				setTimeout(() => window.location.reload(), 1200);
				return;
			}
		}
		pipelineRunning = false;
		pipelineMessage = "La ejecución sigue activa. Puedes revisar su estado en Ejecuciones.";
	}

	function logout() {
		adminToken = "";
		runs = [];
		localStorage.removeItem("jobhunter_admin_token");
	}

	function formatDate(value: string | null) {
		if (!value) return "—";
		return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
	}

	function formatTime(value: string | null) {
		if (!value) return "--:--";
		return new Intl.DateTimeFormat("es-CO", { hour: "2-digit", minute: "2-digit" }).format(new Date(value));
	}

	function runStatusLabel(run: any) {
		if (!run) return "Sin ejecuciones";
		if (run.status === "running") return run.phase_message || "En ejecución";
		if (run.status === "completed") return "Completada";
		return "Con error";
	}
</script>

<svelte:head>
	<title>Job Hunter IA · Ofertas que encajan contigo</title>
	<meta
		name="description"
		content="Panel demostrativo de Job Hunter IA para descubrir oportunidades de empleo compatibles."
	/>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link
		rel="preconnect"
		href="https://fonts.gstatic.com"
		crossorigin="anonymous"
	/>
	<link
		href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<div class="app-shell">
	<aside class="sidebar">
		<div class="brand">
			<div class="brand-mark">
				<span></span><span></span><span></span>
			</div>
			<div>
				<strong>job<span>hunter</span></strong><small
					>INTELLIGENT SEARCH</small
				>
			</div>
		</div>
		<div class="profile-mini">
			<div class="avatar">CD</div>
			<div>
				<strong>Cristian Daniel</strong><small>Perfil activo</small>
			</div>
			<div class="online-dot"></div>
		</div>
		<nav>
			<p class="nav-label">ESPACIO DE TRABAJO</p>
			{#each navItems as item}<button
					class:active={activeNav === item.label}
					onclick={() => item.label === "Ejecuciones" ? openHistory() : item.label === "Cómo funciona" ? openHowItWorks() : (activeNav = item.label)}
					><span class="nav-icon {item.icon}"
					></span>{item.label}{#if item.label === "Ejecuciones"}<span class="lock-label">Admin</span>{/if}</button
				>{/each}
		</nav>
		<div class="sidebar-bottom">
			<div class="pipeline-mini">
				<div class="pipeline-heading">
					<span class="live-dot"></span><span>Pipeline local</span><b
						>Listo</b
					>
				</div>
				<div class="pipeline-line">
					<i class="done"></i><i class="done"></i><i></i>
				</div>
				<div class="pipeline-steps">
					<span>Recolectar</span><span>Analizar</span><span
						>Enviar</span
					>
				</div>
			</div>

		</div>
	</aside>

	<main class="main-content">
		<header class="topbar">
			<div class="mobile-brand">
				<div class="brand-mark">
					<span></span><span></span><span></span>
				</div>
				<strong>jobhunter</strong>
			</div>
			<div class="global-search">
				<span class="search-icon"></span><input
					placeholder="Buscar ofertas, empresas o tecnologías..."
				/>
			</div>
			<div class="top-actions">
				
				<div class="top-avatar">CD</div>
				<button class="user-menu"
					>Cristian <span class="chevron">⌄</span></button
				>
			</div>
		</header>
		<div class="content-wrap">
			<div class="page-heading">
				<div>
					<p class="eyebrow">PANEL DE OPORTUNIDADES</p>
					<h1>Ofertas que encajan contigo<span>.</span></h1>
					<p class="subtitle">
						Tu búsqueda inteligente, filtrada por habilidades,
						ubicación y experiencia.
					</p>
				</div>
				<div class="last-run">
					<span class="live-dot"></span>
					<div>
						<small>Última ejecución</small><strong>{latestRun ? formatDate(latestRun.started_at) : "Sin ejecuciones"}</strong>
					</div>
				</div>
			</div>
			<section class="stats-grid">
				<div class="stat-card">
					<div class="stat-icon purple">⌕</div>
					<div>
						<small>Ofertas encontradas</small><strong
							>{stats.found_today}</strong
						><em class="up">en vivo</em>
					</div>
					<span class="stat-note">hoy</span>
				</div>
				<div class="stat-card">
					<div class="stat-icon green">✦</div>
					<div>
						<small>Compatibles contigo</small><strong
							>{stats.compatible}</strong
						><em class="up">score ≥ 70</em>
					</div>
					<span class="stat-note">analizadas</span>
				</div>
				<div class="stat-card">
					<div class="stat-icon orange">↗</div>
					<div>
						<small>Enviadas a Telegram</small><strong
							>{stats.sent_today}<span
								>/{stats.telegram_limit}</span
							></strong
						><em class="neutral">hoy</em>
					</div>
					<span class="stat-note">límite diario</span>
				</div>
				<div class="stat-card">
					<div class="stat-icon blue">◷</div>
					<div>
						<small>Estado de conexión</small><strong
							>{usingDemo ? "Demo" : "API"}</strong
						><em class="neutral"
							>{usingDemo ? "local" : "activa"}</em
						>
					</div>
					<span class="stat-note">PostgreSQL</span>
				</div>
			</section>
			<div class="section-bar">
				<div>
					<h2>Oportunidades recientes</h2>
					<p>Ordenadas por compatibilidad con tu perfil</p>
				</div>
				<div class="view-actions">
					<button
						class:active={filter === "Todas"}
						onclick={() => (filter = "Todas")}>Todas</button
					><button
						class:active={filter === "Remoto"}
						onclick={() => (filter = "Remoto")}>Remotas</button
					><button
						class:active={filter === "Job API"}
						onclick={() => (filter = "Job API")}>Job API</button
					><button
						class="filter-button"
						class:active={showFilters}
						onclick={() => (showFilters = !showFilters)}
						>☷ <span>Filtros</span></button
					>
				</div>
			</div>
			{#if showFilters}<div class="filter-panel">
					<span>Filtrar por:</span><button
						onclick={() => (filter = "Todas")}>Todas</button
					><button onclick={() => (filter = "Remoto")}>Remoto</button
					><button onclick={() => (filter = "Get on Board")}
						>Get on Board</button
					><button onclick={() => (filter = "Job API")}
						>Job API</button
					>
				</div>{/if}
			<div class="jobs-toolbar">
				<div class="local-search">
					<span class="search-icon"></span><input
						bind:value={search}
						placeholder="Buscar en tus ofertas..."
					/>
				</div>
				<span class="result-count"
					>{filteredJobs.length} ofertas visibles</span
				><select aria-label="Ordenar ofertas"
					><option>Mayor compatibilidad</option><option
						>Más recientes</option
					></select
				>
			</div>
			<div class="jobs-grid">
				{#each filteredJobs as job}<article class="job-card">
						<div class="job-top">
							<div class="company-logo {job.color}">
								{job.company.slice(0, 1)}
							</div>
							<div class="job-heading">
								<h3>{job.title}</h3>
								<p>{job.company}</p>
							</div>
							<button class="bookmark" aria-label="Guardar oferta"
								>♡</button
							>
						</div>
						<div class="job-tags">
							<span class="tag location">⌖ {job.mode}</span><span
								class="tag type">▣ {job.type}</span
							><span class="tag open">Nueva</span>
						</div>
						<p class="job-location">{job.location}</p>
						<p class="job-description telegram-preview">
							{job.telegramMessage || job.description ||
								"Una oportunidad para construir productos digitales y trabajar con un equipo de desarrollo orientado a resultados..."}
						</p>
						<div class="job-bottom">
							<div class="score">
								<div
									class:score-low={scoreTone(job.score) === "low"}
									class:score-medium={scoreTone(job.score) === "medium"}
									class:score-high={scoreTone(job.score) === "high"}
									class:score-excellent={scoreTone(job.score) === "excellent"}
									class="score-ring"
									aria-label={`${job.score}% de compatibilidad`}
								>
									<svg viewBox="0 0 42 42" aria-hidden="true"
										><circle
											class="score-track"
											cx="21"
											cy="21"
											r="16"
										></circle><circle
											class="score-progress"
											cx="21"
											cy="21"
											r="16"
											style={`--progress: ${job.score}`}
										></circle></svg
					><strong>{job.score}<small>%</small></strong
									>
								</div>
								<div>
									<b>Match IA</b><small>{job.time}</small>
								</div>
							</div>
							<span class="source">{job.source}</span>
						</div>
						<div class="card-actions">
							<button class="details" onclick={() => (selectedJob = job)}>Ver detalles</button><a
								href={job.url || "/"}
								target={job.url ? "_blank" : undefined}
								rel="noreferrer"
								onclick={(event) => {
									if (!job.url) event.preventDefault();
								}}>Aplicar ahora <span>↗</span></a
							>
						</div>
					</article>{/each}
			</div>
			<section class="bottom-grid">
				<div class="run-card">
					<div class="card-title">
						<div>
							<p class="eyebrow">ACTIVIDAD DEL SISTEMA</p>
							<h2>Última ejecución</h2>
						</div>
						<span class:running={latestRun?.status === "running"} class="status-pill"><i></i> {runStatusLabel(latestRun)}</span>
					</div>
					<div class="run-flow">
						<div>
							<b>{formatTime(latestRun?.started_at)}</b><span>Recolector</span><small
								>{latestRun?.found_count ?? 0} ofertas</small
							>
						</div>
						<i></i>
						<div>
							<b>{latestRun?.current_step === "analyzing" ? formatTime(latestRun?.updated_at) : latestRun?.ended_at ? formatTime(latestRun.ended_at) : "--:--"}</b><span>Analizador IA</span><small
								>{latestRun?.analyzed_count ?? 0} evaluadas</small
							>
						</div>
						<i></i>
						<div>
							<b>{latestRun?.current_step === "notifying" ? formatTime(latestRun?.updated_at) : latestRun?.ended_at ? formatTime(latestRun.ended_at) : "--:--"}</b><span>Telegram</span><small
								>{latestRun?.notified_count ?? 0} enviadas</small
							>
						</div>
					</div>
					<a
						class="text-link"
						href="/"
						onclick={(event) => { event.preventDefault(); openHistory(); }}
						>Ver historial de ejecuciones <span>→</span></a
					>
				</div>
				<div class="about-card">
					<div class="sparkle">✦</div>
					<p class="eyebrow">JOB HUNTER IA</p>
					<h2>
						Menos ruido.<br /><span>Mejores oportunidades.</span>
					</h2>
					<p>
						Un sistema personal que busca, filtra y explica las
						ofertas que realmente pueden interesarte.
					</p>
					<a href="/" onclick={(event) => { event.preventDefault(); openHowItWorks(); }}
						>Conoce cómo funciona <span>→</span></a
					>
				</div>
			</section>
		</div>
	</main>
</div>

{#if activeNav === "Ejecuciones"}
	<div class="admin-overlay" role="presentation">
		<dialog open class="admin-panel" aria-labelledby="history-title">
			{#if !adminToken}
				<div class="admin-login">
					<button class="close-button" aria-label="Cerrar historial" onclick={() => (activeNav = "Ofertas")}>×</button>
					<div class="admin-login-icon">⌁</div>
					<p class="eyebrow">ÁREA PRIVADA</p>
					<h2 id="history-title">Historial de ejecuciones</h2>
					<p>Inicia sesión para consultar qué hizo el pipeline en cada ejecución.</p>
					<form onsubmit={(event) => { event.preventDefault(); login(); }}>
						<label>Usuario<input bind:value={loginUser} autocomplete="username" required /></label>
						<label>Contraseña<input type="password" bind:value={loginPassword} autocomplete="current-password" required /></label>
						{#if loginError}<div class="login-error">{loginError}</div>{/if}
						<button class="login-button" type="submit">Entrar al historial</button>
					</form>
				</div>
			{:else}
				<div class="admin-header">
					<div><p class="eyebrow">ÁREA PRIVADA</p><h2 id="history-title">Historial de ejecuciones</h2></div>
					<div class="admin-actions"><button class="run-pipeline-button compact" class:running={pipelineRunning} disabled={pipelineRunning} onclick={runPipeline}><span class="run-button-icon">↻</span>{pipelineRunning ? "Ejecutando..." : "Ejecutar pipeline"}</button><button onclick={logout}>Cerrar sesión</button><button class="close-button" aria-label="Cerrar historial" onclick={() => (activeNav = "Ofertas")}>×</button></div>
				</div>
				{#if pipelineMessage}<div class="pipeline-live-message">{pipelineMessage}</div>{/if}
				{#if loadingRuns}
					<div class="history-empty">Cargando ejecuciones...</div>
				{:else if loginError}
					<div class="history-empty login-error">{loginError}</div>
				{:else if runs.length === 0}
					<div class="history-empty">Todavía no hay ejecuciones registradas.</div>
				{:else}
					<div class="runs-list">
						{#each runs as run}
							<article class="run-row">
								<div class="run-row-main"><span class:failed={run.status === "error"} class="run-status-dot"></span><div><strong>{formatDate(run.started_at)}</strong><small>{run.ended_at ? `Finalizó ${formatDate(run.ended_at)}` : "En ejecución"}</small></div></div>
								<span class:run-failed={run.status === "error"} class="run-status">{run.status === "completed" ? "Completada" : run.status === "error" ? "Con error" : "En curso"}</span>
								<div class="run-metrics"><span><b>{run.found_count ?? 0}</b> encontradas</span><span><b>{run.filtered_count ?? 0}</b> filtradas</span><span><b>{run.analyzed_count ?? 0}</b> analizadas</span><span><b>{run.notified_count ?? 0}</b> notificadas</span></div>
								{#if run.error_message}<p class="run-error">{run.error_message}</p>{/if}
							</article>
						{/each}
					</div>
				{/if}
			{/if}
		</dialog>
	</div>
{/if}

{#if activeNav === "Cómo funciona"}
	<div class="info-overlay">
		<section class="info-panel" aria-labelledby="how-title">
			<button class="close-button info-close" aria-label="Cerrar información" onclick={() => (activeNav = "Ofertas")}>×</button>
			<p class="eyebrow">EL SISTEMA EN CINCO PASOS</p>
			<h2 id="how-title">Cómo encuentra oportunidades para ti</h2>
			<p class="info-intro">Job Hunter IA reduce el ruido: primero reúne ofertas, después las filtra y solo usa la IA cuando realmente vale la pena.</p>
			<div class="process-grid">
				<div class="process-step"><span>01</span><div><h3>Recolectar</h3><p>Consulta Get on Board y Job API con búsquedas y ubicaciones que encajan con tu perfil.</p></div></div>
				<div class="process-step"><span>02</span><div><h3>Filtrar y deduplicar</h3><p>Descarta cargos o niveles incompatibles y evita guardar la misma oferta desde dos fuentes.</p></div></div>
				<div class="process-step"><span>03</span><div><h3>Puntuar</h3><p>Cada oferta recibe puntos por cargo, habilidades, ubicación y nivel de experiencia.</p></div></div>
				<div class="process-step"><span>04</span><div><h3>Analizar con IA</h3><p>La IA explica el resumen, las coincidencias, los faltantes y por qué puede encajar contigo.</p></div></div>
				<div class="process-step"><span>05</span><div><h3>Notificar</h3><p>Telegram recibe las mejores ofertas, con un límite diario de 10 para evitar ruido y gasto innecesario.</p></div></div>
			</div>
			<div class="info-note"><strong>Diseñado para ejecutarse localmente</strong><span>El computador ejecuta el pipeline cuando lo enciendes. La web muestra sus resultados y deja preparado el camino para automatizarlo en el futuro.</span></div>
		</section>
	</div>
{/if}

{#if selectedJob}
	<div class="details-overlay">
		<article class="details-panel">
			<div class="details-header"><div><p class="eyebrow">DETALLE DE LA OFERTA</p><h2>{selectedJob.title}</h2><p>{selectedJob.company} · {selectedJob.location}</p></div><button class="close-button" aria-label="Cerrar detalle" onclick={() => (selectedJob = null)}>×</button></div>
			<div class="details-score"><span class={`score-badge score-${scoreTone(selectedJob.score)}`}>{selectedJob.score}%</span><span>compatibilidad con tu perfil</span><span class="source">{selectedJob.source}</span></div>
			<div class="details-message">{selectedJob.telegramMessage || selectedJob.description || "No hay resumen disponible para esta oferta."}</div>
			<div class="details-footer"><button class="details-secondary" onclick={() => (selectedJob = null)}>Cerrar</button><a href={selectedJob.url || "/"} target={selectedJob.url ? "_blank" : undefined} rel="noreferrer" onclick={(event) => { if (!selectedJob?.url) event.preventDefault(); }}>Abrir oferta ↗</a></div>
		</article>
	</div>
{/if}

<style>
	:global(*) {
		box-sizing: border-box;
	}
	:global(body) {
		margin: 0;
		background: #f7f8fc;
		color: #182032;
		font-family: "DM Sans", sans-serif;
	}
	:global(button),
	:global(input),
	:global(select) {
		font: inherit;
	}
	:global(button) {
		cursor: pointer;
	}
	.app-shell {
		min-height: 100vh;
		display: flex;
	}
	.sidebar {
		width: 244px;
		background: #fff;
		border-right: 1px solid #e8eaf1;
		display: flex;
		flex-direction: column;
		padding: 28px 16px 20px;
		position: fixed;
		inset: 0 auto 0 0;
		z-index: 2;
	}
	.brand,
	.mobile-brand {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 0 10px;
	}
	.brand strong,
	.mobile-brand strong {
		font-family: "Space Grotesk";
		font-size: 20px;
		letter-spacing: -1px;
		color: #192034;
	}
	.brand strong span {
		color: #6654e8;
	}
	.brand small {
		display: block;
		color: #a1a6b3;
		font-size: 7px;
		font-weight: 700;
		letter-spacing: 1px;
		margin-top: 2px;
	}
	.brand-mark {
		width: 29px;
		height: 29px;
		border-radius: 10px;
		background: linear-gradient(135deg, #6654e8, #8c63ef);
		display: flex;
		align-items: flex-end;
		justify-content: center;
		gap: 3px;
		padding: 7px;
		box-shadow: 0 5px 12px #725ce33d;
	}
	.brand-mark span {
		width: 3px;
		border-radius: 4px;
		background: #fff;
	}
	.brand-mark span:nth-child(1) {
		height: 8px;
	}
	.brand-mark span:nth-child(2) {
		height: 14px;
	}
	.brand-mark span:nth-child(3) {
		height: 11px;
	}
	.profile-mini {
		margin: 40px 5px 27px;
		padding: 11px 9px;
		background: #f7f7ff;
		border-radius: 13px;
		display: flex;
		align-items: center;
		gap: 9px;
		position: relative;
	}
	.avatar,
	.top-avatar {
		background: #ffd8b4;
		color: #8c4b31;
		font-weight: 700;
		display: grid;
		place-items: center;
		border-radius: 10px;
	}
	.avatar {
		width: 32px;
		height: 32px;
		font-size: 10px;
	}
	.profile-mini strong {
		display: block;
		font-size: 11px;
	}
	.profile-mini small {
		color: #9096a4;
		font-size: 10px;
	}
	.online-dot,
	.live-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: #36c98f;
	}
	.online-dot {
		margin-left: auto;
		align-self: flex-start;
		margin-top: 3px;
	}
	.nav-label,
	.eyebrow {
		color: #a1a6b3;
		font-size: 9px;
		letter-spacing: 1.1px;
		font-weight: 700;
		margin: 0 10px 11px;
	}
	.sidebar nav button,
	.side-link {
		border: 0;
		width: 100%;
		text-align: left;
		background: transparent;
		color: #7b8191;
		display: flex;
		align-items: center;
		gap: 13px;
		padding: 11px 12px;
		border-radius: 9px;
		font-size: 12px;
		margin-bottom: 4px;
	}
	.sidebar nav button.active {
		background: #eeecff;
		color: #5b4ee0;
		font-weight: 700;
	}
	.nav-icon {
		display: inline-block;
		width: 17px;
		height: 17px;
		position: relative;
	}
	.nav-icon.grid:before {
		content: "⊞";
		font-size: 21px;
		position: absolute;
		top: -5px;
	}
	.nav-icon.search:before {
		content: "⌕";
		font-size: 25px;
		position: absolute;
		top: -9px;
	}
	.nav-icon.activity:before {
		content: "⌁";
		font-size: 25px;
		position: absolute;
		top: -9px;
	}
	.nav-icon.info:before {
		content: "ⓘ";
		font-size: 18px;
		position: absolute;
		top: -2px;
	}
	.nav-icon.settings:before {
		content: "⚙";
		font-size: 17px;
	}
	.nav-icon.help:before {
		content: "?";
		border: 1px solid currentColor;
		border-radius: 50%;
		width: 14px;
		height: 14px;
		display: grid;
		place-items: center;
		font-size: 10px;
	}
	.sidebar-bottom {
		margin-top: auto;
	}
	.pipeline-mini {
		margin: 15px 5px 20px;
		padding: 13px 11px;
		border: 1px solid #ececf4;
		border-radius: 13px;
	}
	.pipeline-heading {
		display: flex;
		align-items: center;
		gap: 6px;
		color: #596071;
		font-size: 10px;
	}
	.pipeline-heading b {
		margin-left: auto;
		color: #29ad7a;
		font-size: 9px;
	}
	.pipeline-line {
		display: flex;
		align-items: center;
		margin: 14px 3px 5px;
	}
	.pipeline-line i {
		display: block;
		height: 3px;
		flex: 1;
		background: #e8e9f0;
	}
	.pipeline-line i.done {
		background: #6556e5;
	}
	.pipeline-line i:first-child {
		border-radius: 3px 0 0 3px;
	}
	.pipeline-line i:last-child {
		border-radius: 0 3px 3px 0;
	}
	.pipeline-steps {
		display: flex;
		justify-content: space-between;
		color: #a4a8b5;
		font-size: 7px;
	}
	.side-link {
		font-size: 11px;
		padding-left: 12px;
	}
	.main-content {
		margin-left: 244px;
		width: calc(100% - 244px);
	}
	.topbar {
		height: 76px;
		border-bottom: 1px solid #e9eaf0;
		background: #fff;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 48px;
	}
	.global-search {
		width: 340px;
		height: 38px;
		border: 1px solid #e6e7ed;
		border-radius: 9px;
		display: flex;
		align-items: center;
		padding: 0 13px;
		gap: 10px;
	}
	.global-search input,
	.local-search input {
		border: 0;
		outline: 0;
		width: 100%;
		color: #303749;
		font-size: 11px;
		background: transparent;
	}
	.global-search input::placeholder,
	.local-search input::placeholder {
		color: #a7abb7;
	}
	.search-icon {
		width: 15px;
		height: 15px;
		border: 2px solid #8b92a1;
		border-radius: 50%;
		display: block;
		position: relative;
		flex: 0 0 auto;
	}
	.search-icon:after {
		content: "";
		position: absolute;
		width: 6px;
		height: 2px;
		background: #8b92a1;
		transform: rotate(45deg);
		right: -5px;
		bottom: -2px;
		border-radius: 3px;
	}
	.top-actions {
		display: flex;
		align-items: center;
		gap: 13px;
	}
	.icon-button {
		border: 1px solid #e8e9ee;
		background: #fff;
		border-radius: 10px;
		width: 38px;
		height: 38px;
		position: relative;
	}
	.notification:before {
		content: "♧";
		color: #687080;
		font-size: 21px;
	}
	.notification span {
		width: 5px;
		height: 5px;
		background: #ef6c70;
		position: absolute;
		border-radius: 50%;
		top: 9px;
		right: 10px;
	}
	.top-avatar {
		width: 31px;
		height: 31px;
		font-size: 9px;
		border-radius: 50%;
	}
	.user-menu {
		border: 0;
		background: transparent;
		font-size: 11px;
		color: #4e5565;
	}
	.chevron {
		color: #8b91a0;
		margin-left: 5px;
	}
	.mobile-brand {
		display: none;
	}
	.content-wrap {
		max-width: 1430px;
		margin: 0 auto;
		padding: 42px 48px 65px;
	}
	.page-heading {
		display: flex;
		justify-content: space-between;
		align-items: end;
		margin-bottom: 31px;
	}
	.page-heading h1 {
		font-family: "Space Grotesk";
		font-size: clamp(27px, 3vw, 39px);
		letter-spacing: -1.8px;
		margin: 6px 0 9px;
		color: #161d2c;
	}
	.page-heading h1 span {
		color: #6654e8;
	}
	.subtitle {
		color: #8c92a1;
		font-size: 12px;
		margin: 0;
	}
	.last-run {
		display: flex;
		align-items: center;
		gap: 9px;
		border: 1px solid #e9eaf0;
		background: #fff;
		padding: 10px 14px;
		border-radius: 11px;
	}
	.last-run small,
	.last-run strong {
		display: block;
	}
	.last-run small {
		color: #a0a5b1;
		font-size: 9px;
		margin-bottom: 3px;
	}
	.last-run strong {
		font-size: 11px;
		color: #444b5b;
	}
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 15px;
		margin-bottom: 42px;
	}
	.stat-card {
		min-height: 117px;
		border: 1px solid #e9eaf0;
		background: #fff;
		border-radius: 14px;
		padding: 17px;
		display: grid;
		grid-template-columns: 38px 1fr;
		column-gap: 11px;
		position: relative;
	}
	.stat-icon {
		width: 38px;
		height: 38px;
		border-radius: 10px;
		display: grid;
		place-items: center;
		font-size: 23px;
		grid-row: span 2;
	}
	.stat-icon.purple {
		background: #efedff;
		color: #6958e5;
	}
	.stat-icon.green {
		background: #e8faf2;
		color: #30b580;
	}
	.stat-icon.orange {
		background: #fff3e7;
		color: #eb984b;
	}
	.stat-icon.blue {
		background: #e9f3ff;
		color: #468de3;
	}
	.stat-card small {
		color: #858b9a;
		font-size: 10px;
		display: block;
		margin-bottom: 5px;
	}
	.stat-card strong {
		font-family: "Space Grotesk";
		font-size: 23px;
		letter-spacing: -0.8px;
	}
	.stat-card strong span {
		font-size: 13px;
		color: #afb3bc;
		font-family: "DM Sans";
		font-weight: 500;
	}
	.stat-card em {
		font-style: normal;
		font-size: 9px;
		margin-left: 7px;
	}
	.up {
		color: #2bb483;
	}
	.neutral {
		color: #a4a9b5;
	}
	.stat-note {
		grid-column: 2;
		color: #b0b4bf;
		font-size: 9px;
		margin-top: -3px;
	}
	.section-bar,
	.jobs-toolbar {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.section-bar {
		margin-bottom: 17px;
	}
	.section-bar h2,
	.bottom-grid h2 {
		font-family: "Space Grotesk";
		font-size: 19px;
		margin: 0 0 4px;
		letter-spacing: -0.6px;
	}
	.section-bar p {
		margin: 0;
		color: #999eaa;
		font-size: 11px;
	}
	.view-actions {
		display: flex;
		gap: 6px;
	}
	.view-actions button,
	.filter-panel button {
		border: 0;
		background: transparent;
		color: #969ba8;
		font-size: 10px;
		padding: 8px 10px;
		border-radius: 7px;
	}
	.view-actions button.active,
	.view-actions button:hover,
	.filter-panel button:hover {
		color: #5c50dc;
		background: #efedff;
	}
	.view-actions .filter-button {
		border: 1px solid #dddfe7;
		color: #5d6473;
		margin-left: 8px;
		padding: 7px 13px;
	}
	.filter-panel {
		display: flex;
		gap: 5px;
		align-items: center;
		margin: -7px 0 14px;
		padding: 10px 13px;
		background: #f0efff;
		border-radius: 9px;
		color: #656b7a;
		font-size: 10px;
	}
	.filter-panel button {
		color: #5b50d8;
	}
	.jobs-toolbar {
		margin-bottom: 15px;
	}
	.local-search {
		display: flex;
		align-items: center;
		gap: 9px;
		width: 230px;
		border: 1px solid #e6e7ed;
		background: #fff;
		border-radius: 8px;
		padding: 8px 11px;
	}
	.jobs-toolbar select {
		border: 1px solid #e6e7ed;
		color: #858b98;
		border-radius: 8px;
		background: #fff;
		padding: 8px 10px;
		outline: 0;
		font-size: 10px;
	}
	.result-count {
		color: #a1a6b2;
		font-size: 10px;
		margin-left: auto;
		margin-right: 14px;
	}
	.jobs-grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 15px;
	}
	.job-card {
		border: 1px solid #e8e9ef;
		background: #fff;
		border-radius: 13px;
		padding: 17px;
		transition:
			transform 0.2s,
			box-shadow 0.2s;
	}
	.job-card:hover {
		transform: translateY(-3px);
		box-shadow: 0 12px 25px #30364b0d;
	}
	.job-top {
		display: flex;
		align-items: flex-start;
		gap: 10px;
	}
	.company-logo {
		width: 37px;
		height: 37px;
		border-radius: 11px;
		display: grid;
		place-items: center;
		color: #fff;
		font-family: "Space Grotesk";
		font-weight: 700;
		font-size: 17px;
	}
	.company-logo.violet {
		background: #6658df;
	}
	.company-logo.blue {
		background: #3492dd;
	}
	.company-logo.orange {
		background: #ed9a52;
	}
	.company-logo.lime {
		background: #9bdc43;
		color: #274720;
	}
	.company-logo.cyan {
		background: #31c6d1;
	}
	.company-logo.rose {
		background: #d46976;
	}
	.job-heading {
		min-width: 0;
		flex: 1;
	}
	.job-heading h3 {
		margin: 1px 0 4px;
		font-size: 13px;
		line-height: 1.28;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.job-heading p {
		color: #9297a4;
		font-size: 10px;
		margin: 0;
	}
	.bookmark {
		border: 0;
		background: transparent;
		color: #a6abb7;
		font-size: 22px;
		line-height: 1;
	}
	.job-tags {
		display: flex;
		gap: 5px;
		margin: 15px 0 9px;
	}
	.tag {
		border-radius: 12px;
		padding: 5px 8px;
		font-size: 9px;
	}
	.tag.location {
		background: #edf6ff;
		color: #3b8cda;
	}
	.tag.type {
		background: #fff5df;
		color: #d69b35;
	}
	.tag.open {
		background: #e9f9f0;
		color: #28a874;
	}
	.job-location {
		color: #737a89;
		font-size: 10px;
		margin: 0 0 7px;
	}
	.job-description {
		color: #777d8b;
		line-height: 1.55;
		font-size: 10px;
		min-height: 32px;
		margin: 0 0 15px;
	}
	.job-bottom {
		border-top: 1px solid #f0f0f4;
		padding-top: 12px;
		display: flex;
		align-items: center;
		justify-content: space-between;
	}
	.score {
		display: flex;
		gap: 8px;
		align-items: center;
	}
	.score-ring {
		width: 34px;
		height: 34px;
		position: relative;
		display: grid;
		place-items: center;
		color: #28a977;
		font-size: 10px;
		font-weight: 700;
	}
	.score-ring svg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		transform: rotate(-90deg);
	}
	.score-ring circle {
		fill: none;
		stroke-width: 4;
	}
	.score-track {
		stroke: #e7f4ee;
	}
	.score-progress {
		stroke: #35bd8a;
		stroke-linecap: round;
		stroke-dasharray: 100.53;
		stroke-dashoffset: calc(100.53 - (100.53 * var(--progress)) / 100);
	}
	.score-ring.score-low { color: #d94f5c; }
	.score-ring.score-low .score-track { stroke: #fbe3e5; }
	.score-ring.score-low .score-progress { stroke: #d94f5c; }
	.score-ring.score-medium { color: #e58b2f; }
	.score-ring.score-medium .score-track { stroke: #fff0db; }
	.score-ring.score-medium .score-progress { stroke: #e58b2f; }
	.score-ring.score-high { color: #27a873; }
	.score-ring.score-high .score-track { stroke: #e1f5eb; }
	.score-ring.score-high .score-progress { stroke: #27a873; }
	.score-ring.score-excellent { color: #378bd5; }
	.score-ring.score-excellent .score-track { stroke: #e1effc; }
	.score-ring.score-excellent .score-progress { stroke: #378bd5; }
	.score-ring strong {
		position: relative;
		z-index: 1;
		font-size: 9px;
	}
	.score-ring small {
		font-size: 6px;
	}
	.score b,
	.score small {
		display: block;
	}
	.score b {
		font-size: 9px;
		color: #686f7d;
	}
	.score small {
		color: #a3a8b4;
		font-size: 8px;
		margin-top: 3px;
	}
	.source {
		color: #afb3be;
		font-size: 8px;
		border: 1px solid #ececf0;
		border-radius: 5px;
		padding: 4px 6px;
	}
	.card-actions {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
		margin-top: 14px;
	}
	.card-actions button,
	.card-actions a {
		height: 34px;
		border: 1px solid #dfe1e7;
		border-radius: 7px;
		background: #fff;
		display: grid;
		place-items: center;
		color: #515867;
		font-size: 10px;
		text-decoration: none;
	}
	.card-actions a {
		background: #5d4de2;
		color: #fff;
		border-color: #5d4de2;
		font-weight: 600;
	}
	.card-actions a span {
		margin-left: 5px;
		font-size: 13px;
	}
	.bottom-grid {
		display: grid;
		grid-template-columns: 1.6fr 1fr;
		gap: 15px;
		margin-top: 34px;
	}
	.run-card,
	.about-card {
		border: 1px solid #e8e9ef;
		background: #fff;
		border-radius: 14px;
		padding: 20px;
	}
	.card-title {
		display: flex;
		justify-content: space-between;
		align-items: start;
	}
	.card-title .eyebrow {
		margin-left: 0;
		margin-bottom: 7px;
	}
	.status-pill {
		background: #e9faf2;
		color: #28a977;
		border-radius: 12px;
		padding: 6px 9px;
		font-size: 9px;
	}
	.status-pill i {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		display: inline-block;
		background: currentColor;
		margin-right: 3px;
	}
	.run-flow {
		display: flex;
		align-items: center;
		margin: 27px 8px 21px;
	}
	.run-flow > div {
		text-align: center;
	}
	.run-flow b,
	.run-flow span,
	.run-flow small {
		display: block;
	}
	.run-flow b {
		font-family: "Space Grotesk";
		font-size: 15px;
	}
	.run-flow span {
		color: #616878;
		font-size: 10px;
		margin-top: 4px;
	}
	.run-flow small {
		color: #a3a8b3;
		font-size: 9px;
		margin-top: 4px;
	}
	.run-flow > i {
		height: 1px;
		background: #dedfe8;
		flex: 1;
		margin: 0 18px;
		position: relative;
	}
	.run-flow > i:after {
		content: "›";
		position: absolute;
		right: -3px;
		top: -8px;
		color: #a3a7b4;
	}
	.text-link,
	.about-card a {
		color: #5b4dd7;
		font-size: 10px;
		text-decoration: none;
	}
	.text-link span,
	.about-card a span {
		margin-left: 6px;
	}
	.about-card {
		background: linear-gradient(135deg, #5950d9, #7563e8);
		color: #fff;
		position: relative;
		overflow: hidden;
	}
	.about-card:after {
		content: "";
		width: 170px;
		height: 170px;
		border: 1px solid #ffffff29;
		border-radius: 50%;
		position: absolute;
		right: -60px;
		top: -65px;
		box-shadow:
			0 0 0 22px #ffffff0b,
			0 0 0 44px #ffffff08;
	}
	.about-card .eyebrow {
		color: #d5d1ff;
		margin-left: 0;
	}
	.about-card h2 {
		color: #fff;
		margin-top: 9px;
		font-size: 21px;
		line-height: 1.14;
	}
	.about-card h2 span {
		color: #c8c2ff;
	}
	.about-card p:not(.eyebrow) {
		color: #e0ddff;
		font-size: 10px;
		line-height: 1.6;
		max-width: 255px;
		margin: 14px 0 20px;
	}
	.about-card a {
		color: #fff;
	}
	.sparkle {
		position: absolute;
		right: 22px;
		top: 24px;
		color: #d5d0ff;
		font-size: 22px;
	}
	@media (max-width: 1150px) {
		.sidebar {
			width: 205px;
		}
		.main-content {
			margin-left: 205px;
			width: calc(100% - 205px);
		}
		.topbar,
		.content-wrap {
			padding-left: 30px;
			padding-right: 30px;
		}
		.jobs-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.stats-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	@media (max-width: 760px) {
		.sidebar {
			display: none;
		}
		.main-content {
			margin-left: 0;
			width: 100%;
		}
		.topbar {
			height: 65px;
			padding: 0 18px;
			gap: 15px;
		}
		.mobile-brand {
			display: flex;
			padding: 0;
		}
		.mobile-brand strong {
			font-size: 15px;
		}
		.global-search {
			width: auto;
			flex: 1;
		}
		.top-actions .user-menu {
			display: none;
		}
		.content-wrap {
			padding: 28px 18px 50px;
		}
		.page-heading {
			align-items: flex-start;
			flex-direction: column;
			gap: 19px;
		}
		.last-run {
			align-self: stretch;
		}
		.stats-grid {
			grid-template-columns: 1fr 1fr;
			gap: 9px;
			margin-bottom: 30px;
		}
		.stat-card {
			padding: 12px;
			grid-template-columns: 30px 1fr;
			min-height: 100px;
		}
		.stat-icon {
			width: 30px;
			height: 30px;
			font-size: 18px;
		}
		.stat-card strong {
			font-size: 19px;
		}
		.stat-note {
			font-size: 8px;
		}
		.section-bar {
			display: block;
		}
		.view-actions {
			margin-top: 15px;
			overflow-x: auto;
		}
		.jobs-toolbar select {
			display: none;
		}
		.result-count {
			margin-left: auto;
		}
		.jobs-grid {
			grid-template-columns: 1fr;
		}
		.bottom-grid {
			grid-template-columns: 1fr;
		}
		.run-flow {
			margin-left: 0;
			margin-right: 0;
		}
		.run-flow > i {
			margin: 0 7px;
		}
		.run-flow span {
			font-size: 8px;
		}
	}
	.admin-overlay {
		position: fixed;
		inset: 0;
		z-index: 10;
		background: #18203266;
		backdrop-filter: blur(5px);
		display: grid;
		place-items: center;
		padding: 20px;
	}
	.admin-panel {
		width: min(900px, 100%);
		max-height: 85vh;
		overflow: auto;
		background: #fff;
		border-radius: 20px;
		box-shadow: 0 25px 80px #1820323d;
		padding: 30px;
	}
	.admin-login {
		max-width: 390px;
		margin: 20px auto;
		position: relative;
	}
	.admin-login-icon {
		width: 46px;
		height: 46px;
		border-radius: 14px;
		background: #eeecff;
		color: #6654e8;
		display: grid;
		place-items: center;
		font-size: 28px;
		margin-bottom: 22px;
	}
	.admin-login h2,
	.admin-header h2 {
		font-family: "Space Grotesk";
		font-size: 25px;
		margin: 0 0 8px;
		letter-spacing: -0.8px;
	}
	.admin-login > p:not(.eyebrow) {
		color: #7b8191;
		font-size: 13px;
		line-height: 1.6;
		margin: 0 0 24px;
	}
	.admin-login form {
		display: grid;
		gap: 14px;
	}
	.admin-login label {
		color: #596071;
		font-size: 11px;
		font-weight: 700;
		display: grid;
		gap: 7px;
	}
	.admin-login input {
		border: 1px solid #e2e4ec;
		border-radius: 9px;
		padding: 11px 12px;
		outline: none;
		color: #182032;
	}
	.admin-login input:focus {
		border-color: #6654e8;
		box-shadow: 0 0 0 3px #6654e81c;
	}
	.login-button {
		border: 0;
		border-radius: 9px;
		background: #6654e8;
		color: white;
		font-weight: 700;
		padding: 12px;
		margin-top: 5px;
	}
	.login-error,
	.run-error {
		color: #b54747;
		background: #fff0f0;
		border-radius: 8px;
		padding: 9px 11px;
		font-size: 11px;
	}
	.close-button {
		border: 0;
		background: transparent;
		color: #8c92a0;
		font-size: 26px;
		line-height: 1;
		padding: 2px 6px;
	}
	.admin-login > .close-button {
		position: absolute;
		top: -18px;
		right: -8px;
	}
	.admin-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		border-bottom: 1px solid #ececf4;
		padding-bottom: 20px;
		margin-bottom: 15px;
	}
	.admin-actions {
		display: flex;
		align-items: center;
		gap: 10px;
	}
	.admin-actions > button:first-child {
		border: 1px solid #e2e4ec;
		background: white;
		color: #596071;
		border-radius: 8px;
		padding: 8px 11px;
		font-size: 11px;
	}
	.history-empty {
		padding: 55px 20px;
		text-align: center;
		color: #8b91a0;
		font-size: 13px;
	}
	.runs-list {
		display: grid;
		gap: 10px;
	}
	.run-row {
		border: 1px solid #ececf4;
		border-radius: 13px;
		padding: 16px;
		display: grid;
		grid-template-columns: 1.3fr auto;
		gap: 13px 18px;
	}
	.run-row-main {
		display: flex;
		align-items: flex-start;
		gap: 10px;
	}
	.run-status-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #31bd87;
		margin-top: 5px;
		flex: 0 0 auto;
	}
	.run-status-dot.failed {
		background: #dc6868;
	}
	.run-row strong,
	.run-row small {
		display: block;
	}
	.run-row strong {
		font-size: 13px;
	}
	.run-row small {
		color: #959aa8;
		font-size: 10px;
		margin-top: 3px;
	}
	.run-status {
		align-self: start;
		background: #eaf9f2;
		color: #239267;
		border-radius: 20px;
		padding: 6px 9px;
		font-size: 10px;
		font-weight: 700;
	}
	.run-status.run-failed {
		background: #fff0f0;
		color: #b54747;
	}
	.run-metrics {
		grid-column: 1 / -1;
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.run-metrics span {
		background: #f7f8fc;
		border-radius: 7px;
		padding: 7px 9px;
		color: #858b9b;
		font-size: 10px;
	}
	.run-metrics b {
		color: #333b50;
		font-size: 13px;
		margin-right: 3px;
	}
	.run-error {
		grid-column: 1 / -1;
		margin: 0;
	}
	.lock-label {
		margin-left: auto;
		color: #a0a5b1;
		font-size: 9px;
		font-weight: 500;
	}
	.telegram-preview {
		white-space: pre-line;
		display: -webkit-box;
		-webkit-line-clamp: 13;
		line-clamp: 13;
		-webkit-box-orient: vertical;
		overflow: hidden;
		background: #f7f8fc;
		border: 1px solid #ececf4;
		border-radius: 10px;
		padding: 11px;
		font-size: 10px;
		line-height: 1.55;
		color: #596071;
	}
	.run-pipeline-button {
		border: 0;
		border-radius: 10px;
		background: #6654e8;
		color: #fff;
		font-size: 11px;
		font-weight: 700;
		padding: 11px 14px;
		box-shadow: 0 7px 16px #6654e82b;
	}
	.run-pipeline-button:hover {
		background: #5546d3;
	}
	.run-pipeline-button:disabled {
		cursor: wait;
		opacity: 0.75;
	}
	.run-button-icon {
		display: inline-block;
		font-size: 15px;
		margin-right: 6px;
		vertical-align: -1px;
	}
	.run-pipeline-button.running .run-button-icon {
		animation: spin 1s linear infinite;
	}
	.run-pipeline-button.compact {
		padding: 8px 10px;
		font-size: 10px;
		box-shadow: none;
	}
	.pipeline-live-message {
		background: #f0efff;
		color: #5a50c9;
		border-radius: 9px;
		padding: 9px 12px;
		font-size: 11px;
		margin: -5px 0 14px;
	}
	.status-pill.running {
		background: #fff3df;
		color: #cf7b1f;
	}
	.details-overlay {
		position: fixed;
		inset: 0;
		z-index: 12;
		background: #18203266;
		backdrop-filter: blur(5px);
		display: grid;
		place-items: center;
		padding: 20px;
	}
	.details-panel {
		width: min(680px, 100%);
		max-height: 88vh;
		overflow: auto;
		background: #fff;
		border-radius: 19px;
		box-shadow: 0 25px 80px #1820323d;
		padding: 28px;
	}
	.details-header {
		display: flex;
		justify-content: space-between;
		gap: 15px;
		border-bottom: 1px solid #ececf4;
		padding-bottom: 17px;
	}
	.details-header h2 {
		font-family: "Space Grotesk";
		font-size: 24px;
		letter-spacing: -0.8px;
		margin: 0 0 5px;
	}
	.details-header > div > p:last-child {
		color: #858b9b;
		font-size: 11px;
		margin: 0;
	}
	.details-score {
		display: flex;
		align-items: center;
		gap: 9px;
		padding: 17px 0;
		color: #858b9b;
		font-size: 11px;
	}
	.score-badge {
		border-radius: 20px;
		padding: 7px 10px;
		font-weight: 700;
	}
	.score-badge.score-low { background: #fff0f1; color: #c64351; }
	.score-badge.score-medium { background: #fff3e3; color: #c8791e; }
	.score-badge.score-high { background: #e9f9f1; color: #238c62; }
	.score-badge.score-excellent { background: #eaf3ff; color: #337cc1; }
	.details-score .source {
		margin-left: auto;
	}
	.details-message {
		white-space: pre-line;
		background: #f7f8fc;
		border: 1px solid #ececf4;
		border-radius: 12px;
		padding: 17px;
		color: #596071;
		font-size: 12px;
		line-height: 1.65;
	}
	.details-footer {
		display: flex;
		justify-content: flex-end;
		gap: 9px;
		margin-top: 18px;
	}
	.details-secondary,
	.details-footer a {
		border: 1px solid #e2e4ec;
		border-radius: 8px;
		padding: 9px 12px;
		font-size: 11px;
		text-decoration: none;
	}
	.details-secondary {
		background: #fff;
		color: #697080;
	}
	.details-footer a {
		background: #6654e8;
		border-color: #6654e8;
		color: #fff;
	}
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
	.info-overlay {
		position: fixed;
		inset: 0;
		z-index: 10;
		background: #18203266;
		backdrop-filter: blur(5px);
		display: grid;
		place-items: center;
		padding: 20px;
	}
	.info-panel {
		width: min(860px, 100%);
		max-height: 88vh;
		overflow: auto;
		position: relative;
		background: #fff;
		border-radius: 20px;
		box-shadow: 0 25px 80px #1820323d;
		padding: 34px;
	}
	.info-close {
		position: absolute;
		top: 20px;
		right: 20px;
	}
	.info-panel h2 {
		font-family: "Space Grotesk";
		font-size: clamp(24px, 4vw, 34px);
		letter-spacing: -1px;
		margin: 0 0 10px;
		max-width: 560px;
	}
	.info-intro {
		color: #7b8191;
		font-size: 13px;
		line-height: 1.6;
		max-width: 600px;
		margin: 0 0 26px;
	}
	.process-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 11px;
	}
	.process-step {
		display: flex;
		gap: 13px;
		padding: 15px;
		border: 1px solid #ececf4;
		border-radius: 13px;
	}
	.process-step > span {
		color: #6654e8;
		font-family: "Space Grotesk";
		font-size: 12px;
		font-weight: 700;
	}
	.process-step h3 {
		font-size: 13px;
		margin: 0 0 5px;
	}
	.process-step p {
		color: #858b9b;
		font-size: 11px;
		line-height: 1.5;
		margin: 0;
	}
	.info-note {
		margin-top: 14px;
		padding: 15px;
		border-radius: 12px;
		background: #eeecff;
		color: #5145bd;
		display: grid;
		gap: 4px;
		font-size: 11px;
		line-height: 1.5;
	}
	.info-note span {
		color: #6e65bd;
	}
	@media (max-width: 560px) {
		.admin-panel {
			padding: 22px 16px;
		}
		.admin-header {
			gap: 10px;
		}
		.run-row {
			grid-template-columns: 1fr;
		}
		.run-status {
			justify-self: start;
		}
		.info-panel {
			padding: 26px 18px;
		}
		.process-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
