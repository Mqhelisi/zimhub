import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

import { AuthProvider, useAuth } from './contexts/AuthContext.jsx';
import { DemoModeProvider } from './contexts/DemoModeContext.jsx';
import { NotificationsProvider } from './contexts/NotificationsContext.jsx';
import { ToastProvider } from './components/ui/Toast.jsx';

import { PublicLayout } from './components/layout/PublicLayout.jsx';
import { SuperAdminLayout } from './components/layout/SuperAdminLayout.jsx';
import { ProtectedRoute } from './components/ProtectedRoute.jsx';

import FourPortalHome from './pages/home/FourPortalHome.jsx';
import Login from './pages/auth/Login.jsx';
import Signup from './pages/auth/Signup.jsx';
import PasswordResetRequest from './pages/auth/PasswordResetRequest.jsx';
import PasswordResetConfirm from './pages/auth/PasswordResetConfirm.jsx';
import FirstLoginPasswordChange from './pages/auth/FirstLoginPasswordChange.jsx';

import SellIndex from './pages/sell/SellIndex.jsx';
import ApplySalesman from './pages/sell/ApplySalesman.jsx';
import ApplyPromoter from './pages/sell/ApplyPromoter.jsx';
import ApplyProvider from './pages/sell/ApplyProvider.jsx';
import ApplyCreator from './pages/sell/ApplyCreator.jsx';

import NotificationsPage from './pages/notifications/NotificationsPage.jsx';

// Super admin
import Dashboard from './pages/super/Dashboard.jsx';
import SignupRequestsInbox from './pages/super/SignupRequestsInbox.jsx';
import SignupRequestDetail from './pages/super/SignupRequestDetail.jsx';
import UsersList from './pages/super/UsersList.jsx';
import UserDetail from './pages/super/UserDetail.jsx';
import SystemConfig from './pages/super/SystemConfig.jsx';
import MockMessagesViewer from './pages/super/MockMessagesViewer.jsx';
import DisputesInbox from './pages/super/DisputesInbox.jsx';
import DisputeDetail from './pages/super/DisputeDetail.jsx';

// Stage 2 — Shop section
import ShopSectionLayout from './sections/shop/components/ShopSectionLayout.jsx';
import ShopHome from './sections/shop/pages/ShopHome.jsx';
import ProductsList from './sections/shop/pages/ProductsList.jsx';
import SalesmenList from './sections/shop/pages/SalesmenList.jsx';
import SalesmanProfile from './sections/shop/pages/SalesmanProfile.jsx';
import ProductDetail from './sections/shop/pages/ProductDetail.jsx';
import Cart from './sections/shop/pages/Cart.jsx';
import Checkout from './sections/shop/pages/Checkout.jsx';

// Stage 2 — Salesman admin
import SalesmanLayout from './sections/salesman/components/SalesmanLayout.jsx';
import SalesmanDashboard from './sections/salesman/pages/Dashboard.jsx';
import SalesmanProducts from './sections/salesman/pages/Products.jsx';
import SalesmanProductEditor from './sections/salesman/pages/ProductEditor.jsx';
import SalesmanProfileEditor from './sections/salesman/pages/Profile.jsx';
import SalesmanPendingPayments from './sections/salesman/pages/PendingPayments.jsx';

// Stage 2 — PurchaseInterface buyer pages
import PurchaseDetail from './modules/purchase_interface/pages/PurchaseDetail.jsx';
import MyPurchases from './modules/purchase_interface/pages/MyPurchases.jsx';

// Stage 3 — Events section (public)
import EventsSectionLayout from './sections/events/components/EventsSectionLayout.jsx';
import EventsHome from './sections/events/pages/EventsHome.jsx';
import EventDetailPage from './sections/events/pages/EventDetailPage.jsx';
import EventCheckoutSuccess from './sections/events/pages/EventCheckoutSuccess.jsx';

// ----- Stage 4: Services section + BookingInterface pages -----
import ServicesSectionLayout from './components/services/ServicesSectionLayout.jsx';
import ServicesHome from './pages/services/ServicesHome.jsx';
import ProvidersDirectory from './pages/services/ProvidersDirectory.jsx';
import ProviderProfilePage from './pages/services/ProviderProfilePage.jsx';
import ServiceBookingRequestPage from './pages/services/ServiceBookingRequestPage.jsx';
import BookingRequestSuccessPage from './pages/services/BookingRequestSuccessPage.jsx';
import BuyerBookingsPage from './pages/my/BuyerBookingsPage.jsx';
import BuyerBookingDetailPage from './pages/my/BuyerBookingDetailPage.jsx';
import ProviderLayout from './pages/provider/ProviderLayout.jsx';
import ProviderDashboard from './pages/provider/ProviderDashboard.jsx';
import { ServicesCatalog, ServiceEditor } from './pages/provider/Services.jsx';
import RequestsQueue from './pages/provider/RequestsQueue.jsx';
import ProviderCalendar from './pages/provider/ProviderCalendar.jsx';
import AvailabilityManager from './pages/provider/AvailabilityManager.jsx';
import ProviderProfileEditor from './pages/provider/ProviderProfileEditor.jsx';
import { BookingDisputesInbox, BookingDisputeDetail } from './pages/super/BookingDisputes.jsx';

// Stage 3 — Buyer ticket pages
import BuyerTicketsPage from './pages/my/BuyerTicketsPage.jsx';
import BuyerTicketDetailPage from './pages/my/BuyerTicketDetailPage.jsx';

// Stage 3 — Promoter admin
import PromoterLayout from './sections/promoter/components/PromoterLayout.jsx';
import PromoterDashboard from './sections/promoter/pages/PromoterDashboard.jsx';
import PromoterEventsList from './sections/promoter/pages/PromoterEventsList.jsx';
import EventEditor from './sections/promoter/pages/EventEditor.jsx';
import EventManage from './sections/promoter/pages/EventManage.jsx';
import GatemenManager from './sections/promoter/pages/GatemenManager.jsx';
import PromoterProfileEditor from './sections/promoter/pages/PromoterProfileEditor.jsx';

// Stage 3 — Gate (standalone)
import GateLayout from './sections/gate/components/GateLayout.jsx';
import GateLogin from './sections/gate/pages/GateLogin.jsx';
import GateScan from './sections/gate/pages/GateScan.jsx';

// ----- Stage 5: Creators section + Creator Studio + persistent player -----
import { PlayerProvider } from './contexts/PlayerContext.jsx';
import PersistentPlayer from './modules/creator_platform/components/PersistentPlayer.jsx';
import CreatorsSectionLayout from './pages/creators/CreatorsSectionLayout.jsx';
import CreatorsHome from './pages/creators/CreatorsHome.jsx';
import CreatorProfilePage from './pages/creators/CreatorProfilePage.jsx';
import CreatorMusicPage from './pages/creators/CreatorMusicPage.jsx';
import CreatorGalleryPage from './pages/creators/CreatorGalleryPage.jsx';
import CreatorEventsPage from './pages/creators/CreatorEventsPage.jsx';
import CreatorStudioLayout from './pages/creator-studio/CreatorStudioLayout.jsx';
import CreatorDashboard from './pages/creator-studio/CreatorDashboard.jsx';
import CreatorProfileEditor from './pages/creator-studio/CreatorProfileEditor.jsx';
import MusicManager from './pages/creator-studio/MusicManager.jsx';
import GalleryManager from './pages/creator-studio/GalleryManager.jsx';
import CreatorEventsManager from './pages/creator-studio/CreatorEventsManager.jsx';

// Redirect logged-in users away from /login and /signup.
function RedirectIfAuthed({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) {
    if (user.password_reset_required) return <Navigate to="/change-password" replace />;
    return <Navigate to={user.is_super_admin ? '/super' : '/'} replace />;
  }
  return children;
}

function NotFound() {
  return (
    <div className="container-page py-20 text-center">
      <h1 className="font-display text-6xl text-ink">404</h1>
      <p className="mt-2 text-inkm">That page doesn't exist.</p>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <DemoModeProvider>
        <NotificationsProvider>
          <ToastProvider>
            <PlayerProvider>
              <Routes>
              {/* Public + buyer surfaces */}
              <Route element={<PublicLayout />}>
                <Route path="/" element={<FourPortalHome />} />

                <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
                <Route path="/signup" element={<RedirectIfAuthed><Signup /></RedirectIfAuthed>} />
                <Route path="/password-reset" element={<RedirectIfAuthed><PasswordResetRequest /></RedirectIfAuthed>} />
                <Route path="/password-reset/:token" element={<RedirectIfAuthed><PasswordResetConfirm /></RedirectIfAuthed>} />
                <Route
                  path="/change-password"
                  element={
                    <ProtectedRoute>
                      <FirstLoginPasswordChange />
                    </ProtectedRoute>
                  }
                />

                <Route path="/sell" element={<SellIndex />} />
                <Route path="/sell/salesman" element={<ApplySalesman />} />
                <Route path="/sell/promoter" element={<ApplyPromoter />} />
                <Route path="/sell/provider" element={<ApplyProvider />} />
                <Route path="/sell/creator" element={<ApplyCreator />} />

                <Route
                  path="/notifications"
                  element={
                    <ProtectedRoute>
                      <NotificationsPage />
                    </ProtectedRoute>
                  }
                />

                {/* ----- Stage 2: public Shop section (themed) ----- */}
                <Route element={<ShopSectionLayout />}>
                  <Route path="/shop" element={<ShopHome />} />
                  <Route path="/shop/cart" element={<Cart />} />
                  <Route path="/shop/products" element={<ProductsList />} />
                  <Route path="/shop/salesmen" element={<SalesmenList />} />
                  <Route path="/shop/product/:id" element={<ProductDetail />} />
                  <Route path="/shop/salesman/:slug" element={<SalesmanProfile />} />
                  <Route
                    path="/shop/checkout/:salesmanId"
                    element={
                      <ProtectedRoute>
                        <Checkout />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/shop/checkout/:purchaseId/success"
                    element={
                      <ProtectedRoute>
                        <Checkout />
                      </ProtectedRoute>
                    }
                  />
                </Route>

                {/* ----- Stage 3: public Events section (themed) ----- */}
                <Route element={<EventsSectionLayout />}>
                  <Route path="/events" element={<EventsHome />} />
                  <Route path="/events/:id" element={<EventDetailPage />} />
                  <Route
                    path="/events/:id/checkout/:purchaseId/success"
                    element={
                      <ProtectedRoute>
                        <EventCheckoutSuccess />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/my/tickets"
                    element={
                      <ProtectedRoute>
                        <BuyerTicketsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/my/tickets/:ticketId"
                    element={
                      <ProtectedRoute>
                        <BuyerTicketDetailPage />
                      </ProtectedRoute>
                    }
                  />
                </Route>

                {/* ----- Stage 4: public Services section (themed) ----- */}
                <Route element={<ServicesSectionLayout />}>
                  <Route path="/services" element={<ServicesHome />} />
                  <Route path="/services/providers" element={<ProvidersDirectory />} />
                  <Route path="/services/providers/:slug" element={<ProviderProfilePage />} />
                  <Route
                    path="/services/providers/:slug/book/:serviceId"
                    element={<ServiceBookingRequestPage />}
                  />
                  <Route
                    path="/services/booking/:id/success"
                    element={
                      <ProtectedRoute>
                        <BookingRequestSuccessPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/my/bookings"
                    element={
                      <ProtectedRoute>
                        <BuyerBookingsPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/my/bookings/:id"
                    element={
                      <ProtectedRoute>
                        <BuyerBookingDetailPage />
                      </ProtectedRoute>
                    }
                  />
                </Route>

                {/* ----- Stage 5: public Creators section (themed) ----- */}
                <Route element={<CreatorsSectionLayout />}>
                  <Route path="/creators" element={<CreatorsHome />} />
                  <Route path="/creators/:slug" element={<CreatorProfilePage />} />
                  <Route path="/creators/:slug/music" element={<CreatorMusicPage />} />
                  <Route path="/creators/:slug/gallery" element={<CreatorGalleryPage />} />
                  <Route path="/creators/:slug/events" element={<CreatorEventsPage />} />
                </Route>

                {/* ----- Stage 2: PurchaseInterface buyer pages ----- */}
                <Route
                  path="/my/purchases"
                  element={
                    <ProtectedRoute>
                      <MyPurchases />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/purchases/:id"
                  element={
                    <ProtectedRoute>
                      <PurchaseDetail />
                    </ProtectedRoute>
                  }
                />

                <Route path="*" element={<NotFound />} />
              </Route>

              {/* ----- Stage 2: Salesman admin (own layout) ----- */}
              <Route
                element={
                  <ProtectedRoute>
                    <SalesmanLayout />
                  </ProtectedRoute>
                }
              >
                <Route path="/salesman" element={<SalesmanDashboard />} />
                <Route path="/salesman/products" element={<SalesmanProducts />} />
                <Route path="/salesman/products/new" element={<SalesmanProductEditor />} />
                <Route path="/salesman/products/:id" element={<SalesmanProductEditor />} />
                <Route path="/salesman/profile" element={<SalesmanProfileEditor />} />
                <Route path="/salesman/pending-payments" element={<SalesmanPendingPayments />} />
              </Route>

              {/* ----- Stage 3: Promoter admin (own layout, themed events) ----- */}
              <Route
                element={
                  <ProtectedRoute>
                    <PromoterLayout />
                  </ProtectedRoute>
                }
              >
                <Route path="/promoter" element={<PromoterDashboard />} />
                <Route path="/promoter/events" element={<PromoterEventsList />} />
                <Route path="/promoter/events/new" element={<EventEditor />} />
                <Route path="/promoter/events/:eventId" element={<EventManage />} />
                <Route path="/promoter/events/:eventId/edit" element={<EventEditor />} />
                <Route path="/promoter/events/:eventId/gatemen" element={<GatemenManager />} />
                <Route path="/promoter/profile" element={<PromoterProfileEditor />} />
              </Route>

              {/* ----- Stage 4: Provider admin (own layout, themed services) ----- */}
              <Route
                element={
                  <ProtectedRoute>
                    <ProviderLayout />
                  </ProtectedRoute>
                }
              >
                <Route path="/provider" element={<ProviderDashboard />} />
                <Route path="/provider/services" element={<ServicesCatalog />} />
                <Route path="/provider/services/new" element={<ServiceEditor />} />
                <Route path="/provider/services/:serviceId" element={<ServiceEditor />} />
                <Route path="/provider/requests" element={<RequestsQueue />} />
                <Route path="/provider/calendar" element={<ProviderCalendar />} />
                <Route path="/provider/availability" element={<AvailabilityManager />} />
                <Route path="/provider/profile" element={<ProviderProfileEditor />} />
              </Route>

              {/* ----- Stage 5: Creator Studio (own layout, themed creators) ----- */}
              <Route
                element={
                  <ProtectedRoute>
                    <CreatorStudioLayout />
                  </ProtectedRoute>
                }
              >
                <Route path="/creator" element={<CreatorDashboard />} />
                <Route path="/creator/profile" element={<CreatorProfileEditor />} />
                <Route path="/creator/music" element={<MusicManager />} />
                <Route path="/creator/gallery" element={<GalleryManager />} />
                <Route path="/creator/events" element={<CreatorEventsManager />} />
              </Route>

              {/* ----- Stage 3: Gate (standalone, NO ZimHub chrome) ----- */}
              <Route element={<GateLayout />}>
                <Route path="/gate" element={<Navigate to="/gate/login" replace />} />
                <Route path="/gate/login" element={<GateLogin />} />
                <Route path="/gate/scan" element={<GateScan />} />
              </Route>

              {/* Super Admin */}
              <Route
                element={
                  <ProtectedRoute role="super_admin">
                    <SuperAdminLayout />
                  </ProtectedRoute>
                }
              >
                <Route path="/super" element={<Dashboard />} />
                <Route path="/super/signup-requests" element={<SignupRequestsInbox />} />
                <Route path="/super/signup-requests/:id" element={<SignupRequestDetail />} />
                <Route path="/super/users" element={<UsersList />} />
                <Route path="/super/users/:id" element={<UserDetail />} />
                <Route path="/super/config" element={<SystemConfig />} />
                <Route path="/super/mock-messages" element={<MockMessagesViewer />} />
                <Route path="/super/disputes" element={<DisputesInbox />} />
                <Route path="/super/disputes/:id" element={<DisputeDetail />} />
                <Route path="/super/booking-disputes" element={<BookingDisputesInbox />} />
                <Route path="/super/booking-disputes/:disputeId" element={<BookingDisputeDetail />} />
              </Route>
            </Routes>
              {/* App-global player — rendered above all layouts so audio and
                  the dock survive navigation across every section (hidden on /gate). */}
              <PersistentPlayer />
            </PlayerProvider>
          </ToastProvider>
        </NotificationsProvider>
      </DemoModeProvider>
    </AuthProvider>
  );
}
