import type { Role } from '../api/types.js';
import { hasAnyRole, hasExactRole } from '../app/permissions.js';
import { navigate } from '../app/router.js';
import { icon } from '../components/icons.js';
import { h } from '../utils/dom.js';

export interface WorkspaceCard {
  id: string;
  title: string;
  description: string;
  href: string;
  icon: string;
  roles?: Role[];
  /** Roles that must match directly, without the system-admin override. */
  exactRoles?: Role[];
  badge?: string;
}

export interface WorkspaceGroup {
  title: string;
  description: string;
  cards: WorkspaceCard[];
}

export interface WorkspacePage {
  eyebrow: string;
  title: string;
  description: string;
  groups: WorkspaceGroup[];
}

function cardView(card: WorkspaceCard, emphasized: boolean): HTMLElement {
  return h(
    'button',
    {
      className: `workspace-card card${emphasized ? ' workspace-card--focus' : ''}`,
      type: 'button',
      onClick: () => navigate(card.href),
    },
    h('span', { className: 'workspace-card__icon', 'aria-hidden': 'true' }, icon(card.icon)),
    h('span', { className: 'workspace-card__copy' },
      h('span', { className: 'workspace-card__title' }, card.title),
      h('span', { className: 'workspace-card__description' }, card.description),
    ),
    card.badge ? h('span', { className: 'badge badge--neutral', text: card.badge }) : icon('chevron'),
  );
}

/** Render a task-oriented workspace while keeping its existing resource routes intact. */
export function renderWorkspacePage(workspace: WorkspacePage): HTMLElement {
  const requestedView = new URLSearchParams(location.search).get('view');
  const visibleGroups = workspace.groups
    .map(group => ({
      ...group,
      cards: group.cards.filter(card => card.exactRoles ? hasExactRole(card.exactRoles) : hasAnyRole(card.roles)),
    }))
    .filter(group => group.cards.length);

  return h(
    'section',
    { className: 'page workspace-page' },
    h('div', { className: 'page-heading' },
      h('div', {},
        h('span', { className: 'eyebrow', text: workspace.eyebrow }),
        h('h1', { text: workspace.title }),
        h('p', { text: workspace.description }),
      ),
    ),
    ...visibleGroups.map(group => h(
      'section',
      { className: 'workspace-section', 'aria-label': group.title },
      h('div', { className: 'workspace-section__header' },
        h('h2', { text: group.title }),
        h('p', { text: group.description }),
      ),
      h('div', { className: 'workspace-grid' }, ...group.cards.map(card => cardView(card, requestedView === card.id))),
    )),
  );
}
