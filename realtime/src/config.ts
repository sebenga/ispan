import { config as loadEnv } from 'dotenv';
import { resolve } from 'node:path';

loadEnv({ path: resolve(process.cwd(), '.env') });
loadEnv({ path: resolve(process.cwd(), '..', '.env') });

function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is not set.`);
  }
  return value;
}

function optional(name: string, fallback: string): string {
  return process.env[name] ?? fallback;
}

function list(name: string, fallback: string): string[] {
  return optional(name, fallback)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export const config = {
  port: Number(optional('PORT', optional('REALTIME_PORT', '4000'))),
  redisUrl: optional('REDIS_URL', 'redis://localhost:6379/0'),
  jwtSecret: required('JWT_SIGNING_KEY'),
  jwtAlgorithm: 'HS256' as const,
  corsOrigins: list('REALTIME_CORS_ORIGINS', 'http://localhost:8100,http://localhost:4200'),
  eventChannel: optional('REALTIME_EVENT_CHANNEL', 'ispan:events'),
};
