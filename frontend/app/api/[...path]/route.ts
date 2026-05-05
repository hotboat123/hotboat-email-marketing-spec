import { NextRequest, NextResponse } from "next/server";

// Runtime proxy — reads BACKEND_URL at request time (no rebuild needed).
// Set BACKEND_URL in Railway frontend service Variables.
const BACKEND = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

async function proxy(req: NextRequest): Promise<NextResponse> {
  const path = req.nextUrl.pathname;   // e.g. /api/templates/
  const search = req.nextUrl.search;   // e.g. ?limit=100
  const target = `${BACKEND}${path}${search}`;

  const forward = new Headers();
  for (const [k, v] of req.headers.entries()) {
    const lower = k.toLowerCase();
    if (!["host", "connection", "transfer-encoding", "content-length"].includes(lower)) {
      forward.set(k, v);
    }
  }

  const hasBody = !["GET", "HEAD"].includes(req.method);

  try {
    const upstream = await fetch(target, {
      method: req.method,
      headers: forward,
      body: hasBody ? req.body : undefined,
      // @ts-expect-error duplex needed for streaming request body in Node 18+
      duplex: hasBody ? "half" : undefined,
    });

    const resHeaders = new Headers();
    for (const [k, v] of upstream.headers.entries()) {
      if (!["transfer-encoding", "connection"].includes(k.toLowerCase())) {
        resHeaders.set(k, v);
      }
    }

    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: resHeaders,
    });
  } catch {
    return NextResponse.json({ detail: "Backend no disponible" }, { status: 503 });
  }
}

export const GET    = proxy;
export const POST   = proxy;
export const PATCH  = proxy;
export const DELETE = proxy;
export const PUT    = proxy;
