import { NextRequest, NextResponse } from "next/server"

const BACKEND_URL = process.env.API_URL || "http://localhost:8000"
const API_KEY = process.env.WEBAPP_API_KEY || ""

export async function GET(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params)
}
export async function POST(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params)
}
export async function PUT(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params)
}
export async function PATCH(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params)
}
export async function DELETE(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, await params)
}

async function proxyRequest(req: NextRequest, params: { path: string[] }) {
  const path = params.path.join("/")
  const search = req.nextUrl.search
  const targetUrl = `${BACKEND_URL}/api/${path}${search}`

  const authToken = req.headers.get("authorization") ||
    (req.nextUrl.searchParams.get("_token") ? `Bearer ${req.nextUrl.searchParams.get("_token")}` : "")

  const headers: Record<string, string> = {
    "X-API-Key": API_KEY,
  }
  if (authToken) headers["Authorization"] = authToken

  const contentType = req.headers.get("content-type") || ""
  let body: BodyInit | undefined

  if (req.method !== "GET" && req.method !== "HEAD") {
    if (contentType.includes("multipart/form-data")) {
      const formData = await req.formData()
      body = formData
    } else if (contentType.includes("application/json")) {
      headers["Content-Type"] = "application/json"
      body = await req.text()
    }
  }

  try {
    const res = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
    })

    const resContentType = res.headers.get("content-type") || ""
    if (resContentType.includes("application/json")) {
      const data = await res.json()
      return NextResponse.json(data, { status: res.status })
    }

    const blob = await res.blob()
    const disposition = res.headers.get("content-disposition") || ""
    return new NextResponse(blob, {
      status: res.status,
      headers: {
        "content-type": resContentType,
        ...(disposition ? { "content-disposition": disposition } : {}),
      },
    })
  } catch (e) {
    return NextResponse.json({ detail: "Backend tidak dapat dijangkau" }, { status: 503 })
  }
}
