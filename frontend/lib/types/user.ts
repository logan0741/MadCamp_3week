/**
 * User related types
 */

export interface User {
    id: number;
    username: string;
    is_avatar_created: boolean;
    height: number | null;
    weight: number | null;
    gender: string | null;
    avatar_url: string | null;
}
