// Shop section API client.
import { client as api } from '../../api/client.js';

export const shopApi = {
  // Public read-only
  categories: () => api.get('/api/shop/categories').then((r) => r.data.categories),
  home: () => api.get('/api/shop/home').then((r) => r.data),
  listSalesmen: (params = {}) =>
    api.get('/api/shop/salesmen', { params }).then((r) => r.data),
  salesmanDetail: (slug) =>
    api.get(`/api/shop/salesmen/${slug}`).then((r) => r.data),
  listProducts: (params = {}) =>
    api.get('/api/shop/products', { params }).then((r) => r.data),
  productDetail: (id) =>
    api.get(`/api/shop/products/${id}`).then((r) => r.data.product),

  // Salesman admin
  admin: {
    getProfile: () => api.get('/api/salesman/profile').then((r) => r.data.profile),
    updateProfile: (data) => api.put('/api/salesman/profile', data).then((r) => r.data.profile),
    listProducts: (params = {}) =>
      api.get('/api/salesman/products', { params }).then((r) => r.data),
    getProduct: (id) => api.get(`/api/salesman/products/${id}`).then((r) => r.data.product),
    createProduct: (data) => api.post('/api/salesman/products', data).then((r) => r.data.product),
    updateProduct: (id, data) =>
      api.put(`/api/salesman/products/${id}`, data).then((r) => r.data.product),
    deleteProduct: (id) => api.delete(`/api/salesman/products/${id}`).then((r) => r.data),
    uploadImage: (file) => {
      const fd = new FormData();
      fd.append('file', file);
      return api.post('/api/salesman/uploads/image', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => r.data.url);
    },
    dashboard: () => api.get('/api/salesman/dashboard').then((r) => r.data),
    categories: () => api.get('/api/salesman/categories').then((r) => r.data.categories),
  },
};
