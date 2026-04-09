'use client';

import type { MetaData, RegimeModel } from './types';
import { getRegimeColor, getDimensionColor } from './constants';
import { PanelCard, StatLabel } from './SharedComponents';

interface Props {
  meta: MetaData;
  model?: RegimeModel;
}

export function ModelTab({ meta, model }: Props) {
  if (!meta) {
    return <p className="text-muted-foreground text-[12.5px]">No methodology data.</p>;
  }

  return (
    <div className="space-y-4">
      <PanelCard>
        <h2 className="text-base font-bold text-foreground">{meta.model_name}</h2>
        <p className="text-[12.5px] text-muted-foreground mt-1">{meta.description}</p>
      </PanelCard>

      {/* Regime definitions */}
      {meta.regime_definitions && (
        <PanelCard>
          <StatLabel>Regime Definitions</StatLabel>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(meta.regime_definitions).map(([name, def]) => {
              const color = getRegimeColor(name, model);
              return (
                <div
                  key={name}
                  className="panel-card p-3"
                  style={{ borderLeft: `3px solid ${color}` }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold" style={{ color }}>{name}</span>
                    <span className="text-[10.5px] font-mono text-muted-foreground/60">
                      Growth {def.growth} · Inflation {def.inflation}
                    </span>
                  </div>
                  <p className="text-[11.5px] text-muted-foreground">{def.description}</p>
                </div>
              );
            })}
          </div>
        </PanelCard>
      )}

      {/* Methodology */}
      <PanelCard>
        <StatLabel>Methodology</StatLabel>
        <div className="mt-3 space-y-2">
          {Object.entries(meta.methodology).map(([key, value]) => (
            <div key={key} className="grid grid-cols-1 md:grid-cols-4 gap-2">
              <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground/60 font-mono">
                {key.replace(/_/g, ' ')}
              </div>
              <div className="md:col-span-3 text-[11.5px] text-foreground">
                {value}
              </div>
            </div>
          ))}
        </div>
      </PanelCard>

      {/* Indicator documentation */}
      {meta.indicator_docs &&
        Object.entries(meta.indicator_docs).map(([dim, docs]) => {
          const color = getDimensionColor(dim, model);
          return (
            <PanelCard key={dim}>
              <div className="flex items-center justify-between mb-2">
                <StatLabel>{dim} Indicators</StatLabel>
                <span
                  className="text-[10.5px] uppercase tracking-wider"
                  style={{ color }}
                >
                  {docs.indicators.length} components
                </span>
              </div>
              <p className="text-[11.5px] text-muted-foreground mb-3">{docs.description}</p>
              <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-border/30 text-muted-foreground/60 uppercase tracking-wider text-[10px]">
                      <th className="text-left py-2 px-2">Indicator</th>
                      <th className="text-left py-2 px-2">Code</th>
                      <th className="text-center py-2 px-2">Lag</th>
                      <th className="text-left py-2 px-2">Type</th>
                      <th className="text-left py-2 px-2">Rationale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docs.indicators.map((ind) => (
                      <tr key={ind.name} className="border-b border-border/20 hover:bg-card/50">
                        <td className="py-1.5 px-2 font-semibold" style={{ color }}>
                          {ind.name}
                        </td>
                        <td className="py-1.5 px-2 font-mono text-muted-foreground text-[10.5px]">
                          {ind.code}
                        </td>
                        <td className="py-1.5 px-2 text-center font-mono">{ind.lag}m</td>
                        <td className="py-1.5 px-2 text-muted-foreground">{ind.type}</td>
                        <td className="py-1.5 px-2 text-muted-foreground/80">{ind.rationale}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </PanelCard>
          );
        })}
    </div>
  );
}
