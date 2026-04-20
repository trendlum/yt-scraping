import { createBrowserRouter } from "react-router";
import { Root } from "./components/Root";
import { Overview } from "./components/screens/Overview";
import { Niches } from "./components/screens/Niches";
import { Channels } from "./components/screens/Channels";
import { Topics } from "./components/screens/Topics";
import { Videos } from "./components/screens/Videos";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, Component: Overview },
      { path: "niches", Component: Niches },
      { path: "channels", Component: Channels },
      { path: "topics", Component: Topics },
      { path: "videos", Component: Videos },
    ],
  },
]);
