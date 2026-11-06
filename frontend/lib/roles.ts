/**
 * Admin role definitions and permission helpers.
 * Phase C — role-based visibility backed by backend `deps.py` + Phase B audit.
 */
import type { UserRole } from './types';

export const ADMIN_ROLES: UserRole[] = [
  'administrator',
  'developer',
  'super_admin',
];

export const SUPER_ROLES: UserRole[] = ['super_admin'];

export const CAN_MODIFY: UserRole[] = [
  'administrator',
  'developer',
  'super_admin',
];

export function isAdmin(role?: UserRole | null): boolean {
  return !!role && ADMIN_ROLES.includes(role);
}

export function isSuper(role?: UserRole | null): boolean {
  return !!role && SUPER_ROLES.includes(role);
}

export function canModify(role?: UserRole | null): boolean {
  return !!role && CAN_MODIFY.includes(role);
}
