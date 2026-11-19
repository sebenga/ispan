import jwt from 'jsonwebtoken';
import type { Handshake } from 'socket.io/dist/socket-types';

import { config } from './config.js';

export interface AuthenticatedUser {
  id: string;
  email?: string;
}

interface AccessToken extends jwt.JwtPayload {
  user_id?: string;
  sub?: string;
}

export function extractToken(handshake: Handshake): string | null {
  const auth = handshake.auth as { token?: string } | undefined;
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
