import React from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";
import { store } from "./store";
import App from "./App";
import "./index.css";

import { ConfigProvider } from "antd";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Provider store={store}>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: "#c59b27",
            colorBgBase: "#ffffff",
            colorBgContainer: "#ffffff",
            colorBgLayout: "#fcfaf5",
            colorText: "#1d2b3a",
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
            borderRadius: 8,
          },
          components: {
            Layout: {
              siderBg: "#1d2b3a",
              headerBg: "#fcfaf5",
            },
            Menu: {
              darkItemBg: "#1d2b3a",
              darkItemSelectedBg: "linear-gradient(90deg, #d4af37 0%, #c59b27 100%)",
              darkItemSelectedColor: "#fff",
              darkItemColor: "#a3b1c6",
              darkItemHoverColor: "#fff",
            }
          }
        }}
      >
        <App />
      </ConfigProvider>
    </Provider>
  </React.StrictMode>
);
