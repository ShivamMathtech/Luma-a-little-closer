export type User = {
  id: string;
  username: string;
  display_name: string;
  bio: string;
  website: string;
  avatar_id: string | null;
  is_private: boolean;
};
export type Me = User & {
  email: string;
  is_verified: boolean;
  role: "user" | "admin";
};
export type Profile = User & {
  followers_count: number;
  following_count: number;
  posts_count: number;
  is_following: boolean;
  follow_requested: boolean;
};
export type Asset = {
  id: string;
  url: string;
  mime_type: string;
  width: number | null;
  height: number | null;
  status: string;
  alt_text?: string;
};
export type Post = {
  id: string;
  author: User;
  caption: string;
  kind: "post" | "reel";
  created_at: string;
  media: Asset[];
  likes_count: number;
  comments_count: number;
  is_liked: boolean;
  is_saved: boolean;
};
export type Comment = {
  id: string;
  post_id: string;
  author: User;
  parent_id: string | null;
  body: string;
  created_at: string;
  likes_count: number;
  is_liked: boolean;
};
export type Page<T> = { items: T[]; next_cursor: string | null };
export type Story = {
  id: string;
  author: User;
  media: Asset;
  caption: string;
  expires_at: string;
  is_viewed: boolean;
  views_count: number | null;
};
export type Notice = {
  id: string;
  actor: User;
  kind: string;
  target_id: string | null;
  is_read: boolean;
  created_at: string;
};
export type Message = {
  id: string;
  sender_id: string;
  body: string;
  created_at: string;
  client_id: string;
  attachments: Asset[];
};
export type Conversation = {
  id: string;
  members: User[];
  last_message: Message | null;
  unread_count: number;
};
export type History = Page<Message> & {
  members: { user: User; last_read_at: string }[];
};
export type Collection = { id: string; name: string };
export type SearchResult = {
  users: User[];
  hashtags: { tag: string; count: number }[];
};
export type Report = {
  id: string;
  target_type: "post" | "comment" | "user";
  target_id: string;
  reason: string;
  status: string;
  created_at: string;
};
