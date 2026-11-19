/**
 * Socket.IO gateway for iSpan.
 * Django owns durable state; this process fans out Redis envelopes and
 * proxies chat/location/SOS writes back to Django so the DB stays authoritative.
 */

import express from 'express';
import { createServer } from 'node:http';
import { Redis } from 'ioredis';
import { Server as SocketServer } from 'socket.io';

import { extractToken, verifyAccessToken } from './auth.js';
import { config } from './config.js';
import { authorizeRoom, proxyJobPost } from './django.js';

declare module 'socket.io' {
  interface Socket {
    user?: { id: string; email?: string };
    accessToken?: string;
  }
}

const app = express();
const httpServer = createServer(app);
const io = new SocketServer(httpServer, {
  cors: { origin: config.corsOrigins, credentials: true },
  connectionStateRecovery: {
    maxDisconnectionDuration: 2 * 60 * 1000,
    skipMiddlewares: false,
  },
});

let redisOk = false;
const subscriber = new Redis(config.redisUrl, {
  maxRetriesPerRequest: 1,
  lazyConnect: true,
});

subscriber.on('ready', () => {
  redisOk = true;
});
subscriber.on('error', (err) => {
  redisOk = false;
  console.warn('Realtime Redis error', err.message);
});

app.get('/healthz', (_req, res) => {
  res.json({
    status: 'ok',
    service: 'ispan-realtime',
    sockets: io.engine.clientsCount,
    channel: config.eventChannel,
    redis: redisOk ? 'up' : 'down',
  });
});

io.use((socket, next) => {
  const token = extractToken(socket.handshake);
  if (!token) {
    next(new Error('Access token required'));
    return;
  }
  try {
    socket.user = verifyAccessToken(token);
    socket.accessToken = token;
    next();
  } catch {
    next(new Error('Invalid or expired access token'));
  }
});

io.on('connection', (socket) => {
  const user = socket.user;
  if (!user) {
    socket.disconnect(true);
    return;
  }

  void socket.join(`user:${user.id}`);

  socket.on('subscribe', async (rooms: unknown, ack?: (result: unknown) => void) => {
    const requested = (Array.isArray(rooms) ? rooms : [rooms]).filter(
      (room): room is string => typeof room === 'string',
    );
    const joined: string[] = [];
    const denied: string[] = [];
    for (const room of requested) {
      const ok = await authorizeRoom(user.id, room);
      if (ok) {
        await socket.join(room);
        joined.push(room);
      } else {
        denied.push(room);
      }
    }
    ack?.({ joined, denied });
  });

  socket.on('presence:worker', (payload: { available?: boolean }) => {
    // Presence is advisory for clients; durable availability stays on WorkerProfile via REST.
    io.to(`user:${user.id}`).emit('presence:worker', {
      user_id: user.id,
      available: Boolean(payload?.available),
    });
  });

  socket.on(
    'job:location',
    async (
      payload: { job_id?: string; lat?: number; lng?: number; accuracy_m?: number },
      ack?: (result: unknown) => void,
    ) => {
      if (!payload?.job_id || payload.lat == null || payload.lng == null || !socket.accessToken) {
        ack?.({ ok: false, code: 'invalid_payload' });
        return;
      }
      const result = await proxyJobPost(
        `/jobs/${payload.job_id}/location/`,
        socket.accessToken,
        {
          lat: payload.lat,
          lng: payload.lng,
          accuracy_m: payload.accuracy_m,
        },
      );
      ack?.(result);
    },
  );

  socket.on(
    'job:chat',
    async (payload: { job_id?: string; body?: string }, ack?: (result: unknown) => void) => {
      if (!payload?.job_id || !payload.body || !socket.accessToken) {
        ack?.({ ok: false, code: 'invalid_payload' });
        return;
      }
      const result = await proxyJobPost(`/jobs/${payload.job_id}/chat/`, socket.accessToken, {
        body: payload.body,
      });
      ack?.(result);
    },
  );

  socket.on(
    'sos:trigger',
    async (
      payload: { job_id?: string; lat?: number; lng?: number; note?: string },
      ack?: (result: unknown) => void,
    ) => {
      if (!payload?.job_id || !socket.accessToken) {
        ack?.({ ok: false, code: 'invalid_payload' });
        return;
      }
      const result = await proxyJobPost(`/jobs/${payload.job_id}/sos/`, socket.accessToken, {
        lat: payload.lat,
        lng: payload.lng,
        note: payload.note,
      });
      ack?.(result);
    },
  );

  socket.on('offer:seen', (payload: { offer_id?: string }) => {
    if (payload?.offer_id) {
      socket.emit('offer:seen', { offer_id: payload.offer_id, user_id: user.id });
    }
  });
});

async function start() {
  try {
    await subscriber.connect();
    await subscriber.subscribe(config.eventChannel);
    subscriber.on('message', (_channel, raw) => {
      try {
        const envelope = JSON.parse(raw) as {
          event: string;
          rooms: string[];
          payload: unknown;
        };
        for (const room of envelope.rooms ?? []) {
          io.to(room).emit(envelope.event, envelope.payload);
        }
      } catch (err) {
        console.error('Bad realtime envelope', err);
      }
    });
  } catch (err) {
    console.warn('Realtime continuing without Redis pub/sub', err);
  }

  httpServer.listen(config.port, '0.0.0.0', () => {
    console.log(`iSpan realtime listening on 0.0.0.0:${config.port}`);
  });
}

void start();
