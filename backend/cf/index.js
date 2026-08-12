// Worker front for the volcano-audio seismic collector container.
// Mirrors the webgpu-trading cgs-container pattern: a Python container
// (Flask, port 8080) behind a Worker that proxies HTTP and fires the
// 10-minute collection cron. Replaces the Railway deployment.
//
// Routes: everything is proxied straight to the Flask app (/health,
// /status, /trigger, /api/stream-audio, /api/upload-user-data, ...).
// /worker-health answers without waking the container.

import { Container, getContainer } from "@cloudflare/containers";

export class VolcanoCollector extends Container {
  defaultPort = 8080;
  // Long enough that a collection run (~10-60s) never gets killed mid-run;
  // short enough that we only pay for ~2-3 awake minutes per 10-minute cycle.
  sleepAfter = "2m";
  // Container must reach IRIS FDSN + R2 S3 API
  enableInternet = true;

  constructor(ctx, env) {
    super(ctx, env);
    // Secrets/vars flow from the Worker into the container's process env.
    // SMTP + zone-purge values are optional; endpoints degrade gracefully.
    this.envVars = {
      R2_ACCOUNT_ID: env.R2_ACCOUNT_ID ?? "",
      R2_BUCKET_NAME: env.R2_BUCKET_NAME ?? "",
      R2_ACCESS_KEY_ID: env.R2_ACCESS_KEY_ID ?? "",
      R2_SECRET_ACCESS_KEY: env.R2_SECRET_ACCESS_KEY ?? "",
      CLOUDFLARE_ZONE_ID: env.CLOUDFLARE_ZONE_ID ?? "",
      CLOUDFLARE_API_TOKEN: env.PURGE_API_TOKEN ?? "",
      SMTP_USERNAME: env.SMTP_USERNAME ?? "",
      SMTP_PASSWORD: env.SMTP_PASSWORD ?? "",
    };
  }

  // Internal-only: the cron handler calls this after a collection run
  // completes so the container stops IMMEDIATELY instead of waiting out
  // sleepAfter (observed not reaping the instance between cron cycles —
  // billing depends on this). Blocked from public traffic in the Worker.
  async fetch(request) {
    if (new URL(request.url).pathname === "/__stop") {
      try {
        // destroy(), not stop(): stop() sends SIGTERM, which a container
        // image without a signal handler ignores (PID 1). destroy() is a
        // hard kill — always works, and there's nothing in flight post-run.
        await this.destroy();
      } catch (e) {
        console.log(`__stop: ${e.message}`);
      }
      return new Response(JSON.stringify({ stopped: true }), {
        headers: { "Content-Type": "application/json" },
      });
    }
    return super.fetch(request);
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Worker-level health (does NOT wake the container)
    if (url.pathname === "/worker-health") {
      return new Response(
        JSON.stringify({ status: "ok", worker: "volcano-collector" }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    // Internal lifecycle route — never reachable from outside
    if (url.pathname === "/__stop") {
      return new Response("not found", { status: 404 });
    }

    // Everything else: wake the container (if asleep) and proxy through.
    const container = getContainer(env.COLLECTOR);
    return container.fetch(request);
  },

  // Fires at :02, :12, :22, :32, :42, :52 — same schedule Railway ran.
  async scheduled(controller, env, ctx) {
    ctx.waitUntil(runScheduledCollection(env));
  },
};

async function runScheduledCollection(env) {
  const container = getContainer(env.COLLECTOR);

  const trigger = await container.fetch(
    new Request("http://collector/trigger")
  );
  console.log(`cron: /trigger -> ${trigger.status}`);

  // /trigger returns immediately and runs collection in a background thread.
  // Poll /collector-state until the run finishes (fast at first — steady-state
  // runs take ~5-10s — then slower for long backfill runs), then explicitly
  // stop the container so we only pay for the seconds we actually use.
  let elapsed = 0;
  while (elapsed < 600) {
    const step = elapsed < 60 ? 5 : 15;
    await new Promise((r) => setTimeout(r, step * 1000));
    elapsed += step;
    try {
      const resp = await container.fetch(
        new Request("http://collector/collector-state")
      );
      const state = await resp.json();
      if (!state.currently_running) {
        console.log(`cron: collection complete at ${state.last_run_completed}`);
        await container.fetch(new Request("http://collector/__stop"));
        console.log("cron: container stopped");
        return;
      }
    } catch (e) {
      console.log(`cron: poll error — ${e.message}`);
    }
  }
  // Run still going after 10 min — do NOT kill it mid-run; sleepAfter reaps it.
  console.log("cron: run still going after 10 min; leaving it to finish");
}
