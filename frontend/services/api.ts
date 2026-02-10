import apiClient from './apiClient';

apiClient.defaults.headers.common['Content-Type'] = 'application/json';

export const api = apiClient;
