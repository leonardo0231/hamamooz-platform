import { onUnauthorized } from './api/client.js';
import { initRouter, navigate, renderRoute } from './app/router.js';
import { mountToasts } from './components/feedback.js';

initRouter();
mountToasts();
onUnauthorized(() => navigate('/login', true));
void renderRoute();
