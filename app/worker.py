import asyncio
import json
import socket
import geoip2.database
import redis.asyncio as aioredis
from app.config import settings

async def resolve_reverse_dns(ip: str) -> str:
    """Execute a non-blocking network lookup to discover hostnames/companies."""
    loop = asyncio.get_event_loop()
    try: 
        # offload blocking socket calls to the internal executor pool
        hostname, _, _ = await loop.run_in_executor(None, socket.gethostbyaddr, ip)
        return hostname
    except Exception:
        return "Unknown ISP/Corporate Network"
    
async def process_visitor_logs():
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    print("Analytics Worker Initialized. Awaiting events from 'visitor_stream'...")
    
    # initialize MaxMind Reader
    try:
        geo_reader = geoip2.database.Reader("geoip/GeoLite2-City.mmdb")
    except Exception as e:
        print(f"GeoLite2 Database missing or invalid. Skipping geolocation parsing: {e}")
        geo_reader = None
        
    while True:
        try:
            # block and read entries from the stream
            events = await redis_client.xread({"visitor_stream": "0-0"}, count=1, block=5000)
            if not events:
                continue
            
            for stream, messages in events:
                for msg_id, payload in messages:
                    data = json.loads(payload["data"])
                    ip = data["ip"]
                    
                    # execute background intelligence
                    rdns_host = await resolve_reverse_dns(ip)
                    
                    geo_data = {"city": "Unknown", "country": "Unknown"}
                    if geo_reader and ip not in ("127.0.0.1", "localhost"):
                        try:
                            response = geo_reader.city(ip)
                            geo_data["city"] = response.city.name or "Unknown"
                            geo_data["Country"] = response.country.name or "Unknown"
                        except Exception:
                            pass
                        
                    # compile enriched analytics profile
                    enriched_log = {
                        "ip": ip,
                        "endpoint": data["endpoint"],
                        "reverse_dns": rdns_host,
                        "geolocation": geo_data,
                        "processed_at": data["timestamp"]
                    }
                    
                    print(f" [PROFILED VISIT] {enriched_log['ip']} | Loc: {geo_data['city']}, {geo_data['country']} | Host: {rdns_host}")
                    
                    # acknowledge and remove entry safely from the pipeline
                    await redis_client.xdel("visitor_stream", msg_id)
                    
        except Exception as e:
            print(f"Worker Loop Exception: {e}")
            await asyncio.sleep(2)
                
if __name__ == "__main__":
    asyncio.run(process_visitor_logs())
    