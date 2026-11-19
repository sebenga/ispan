/**
 * Socket.IO gateway for iSpan.
 * Django publishes events to Valkey/Redis; this process fans them out to rooms.
 * Django remains the source of truth.
 */

import express from 'express';
import { createServer } from 'node:http';
import { Redis } from 'ioredis';
import { Server as SocketServer } from 'socket.io';

import { extractToken, verifyAccessToken } from './auth.js';
import { config } from './config.js';

declare module 'socket.io' {
  interface Socket {
    user?: { id: string; email?: string };
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
  enableOfflineOnError: false,
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
    const allowed = requested.filter(
      (room) => room === `user:${user.id}` || room.startsWith('job:'),
    );
    if (allowed.length) await socket.join(allowed);
    ack?.({ joined: allowed });
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
