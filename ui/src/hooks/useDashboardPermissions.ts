'use client';

import { useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import type { ChartMeta } from '@/types/chart';

export interface DashboardPermissions {
  isOwner: boolean;
  isAdminRole: boolean;
  canManageVisibility: boolean;
  canRefreshAll: boolean;
  canReorder: boolean;
  canEditChart: (chart: ChartMeta) => boolean;
  canDeleteChart: (chart: ChartMeta) => boolean;
  canRefreshChart: (chart: ChartMeta) => boolean;
}

export function useDashboardPermissions(): DashboardPermissions {
  const { user } = useAuth();

  const role = String(user?.role || '').toLowerCase();
  const isOwner = !!user && role === 'owner';
  const isAdminRole = !!user && (role === 'admin' || user.is_admin);
  const currentUserId = user?.id || null;

  const isChartOwner = useCallback(
    (chart: ChartMeta) => {
      if (!currentUserId || !chart.created_by_user_id) return false;
      return String(chart.created_by_user_id) === String(currentUserId);
    },
    [currentUserId]
  );

  const canEditChart = useCallback(
    (chart: ChartMeta) => isOwner || isChartOwner(chart),
    [isOwner, isChartOwner]
  );

  const canRefreshChart = useCallback(
    (chart: ChartMeta) => isOwner || isAdminRole || isChartOwner(chart),
    [isOwner, isAdminRole, isChartOwner]
  );

  return {
    isOwner,
    isAdminRole,
    canManageVisibility: isOwner,
    canRefreshAll: isOwner || isAdminRole,
    canReorder: isOwner,
    canEditChart,
    canDeleteChart: canEditChart,
    canRefreshChart,
  };
}
