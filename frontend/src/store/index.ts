import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice";
import customerReducer from "./customerSlice";
import ticketReducer from "./ticketSlice";
import tenantReducer from "./tenantSlice";
import companyReducer from "./companySlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    customers: customerReducer,
    tickets: ticketReducer,
    tenant: tenantReducer,
    companies: companyReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
