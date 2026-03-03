import functools
import redis
import json
from typing import Callable, Any

# Placeholder for Redis connection. In a real app, this would be configured.
# For example, from a central configuration object.
REDIS_CLIENT = redis.StrictRedis(decode_responses=True)

def cache_result(ttl: int = 3600):
    """
    A decorator to cache the results of a connector's method in Redis.
    
    The cache key is generated from the function's module, name, and arguments.
    
    Args:
        ttl: Time-to-live for the cache entry in seconds.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate a cache key based on the function and its arguments
            # self = args[0]
            key_parts = [
                func.__module__, 
                func.__name__,
                str(args[1:]), # Exclude 'self'
                str(sorted(kwargs.items()))
            ]
            cache_key = ":".join(filter(None, key_parts))

            # Try to get the result from cache
            try:
                cached_value = REDIS_CLIENT.get(cache_key)
                if cached_value:
                    return json.loads(cached_value)
            except redis.exceptions.RedisError as e:
                # If Redis is down, log the error and proceed without caching
                print(f"Redis error: {e}")
                cached_value = None

            # If not in cache, execute the function
            result = func(*args, **kwargs)

            # Serialize the result before storing. Pydantic models need to be
            # converted to a serializable format (like dicts).
            if result is not None:
                # This assumes the result is a list of Pydantic models or a single model
                if isinstance(result, list):
                    serializable_result = [item.dict() for item in result]
                else:
                    serializable_result = result.dict()
                
                try:
                    REDIS_CLIENT.setex(cache_key, ttl, json.dumps(serializable_result))
                except redis.exceptions.RedisError as e:
                    print(f"Redis error: {e}")

            return result
        return wrapper
    return decorator
