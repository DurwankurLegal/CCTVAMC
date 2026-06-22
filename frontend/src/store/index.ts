import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice";
import customerReducer from "./customerSlice";
import ticketReducer from "./ticketSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    customers: customerReducer,
    tickets: ticketReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
