import jwt from 'jsonwebtoken';

import { config } from './config.js';

export interface AuthenticatedUser {
  id: string;
  email?: string;
}

interface AccessToken extends jwt.JwtPayload {
  user_id?: string;
  sub?: string;
}

type HandshakeLike = {
  auth?: { token?: string };
  headers: { authorization?: string };
  query: Record<string, string | string[] | undefined>;
};

export function extractToken(handshake: HandshakeLike): string | null {
  const auth = handshake.auth;
  if (auth?.token) return auth.token;
  const header = handshake.headers.authorization;
  if (header?.startsWith('Bearer ')) return header.slice(7);
  const q = handshake.query.token;
  return typeof q === 'string' ? q : null;
}

export function verifyAccessToken(token: string): AuthenticatedUser {
  const claims = jwt.verify(token, config.jwtSecret, {
    algorithms: [config.jwtAlgorithm],
  }) as AccessToken;
  const id = String(claims.user_id ?? claims.sub ?? '');
  if (!id) throw new Error('Token missing user id');
  return { id, email: typeof claims.email === 'string' ? claims.email : undefined };
}
