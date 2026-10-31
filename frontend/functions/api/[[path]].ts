interface Env {
  API_ORIGIN?: string;
}

export const onRequest: PagesFunction<Env> = async (context) => {
  const { request, env } = context;
  const origin = env.API_ORIGIN || "https://outstanding-accurately-syndication-demonstrated.trycloudflare.com";
  
  const url = new URL(request.url);
  // Strip /api prefix when forwarding to target if target is root, or keep it if target expects /api
  // Since FastAPI router is mounted at /api, we keep the path as url.pathname + url.search
  const targetUrl = new URL(url.pathname + url.search, origin.replace(/\/api\/?$/, ""));
  
  // Forward request with all headers and body
  const init: RequestInit = {
    method: request.method,
    headers: request.headers,
    redirect: "follow",
  };
  
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = request.body;
  }
  
  return fetch(new Request(targetUrl.toString(), init));
};
