import { NavigationMenu, NavigationMenuItem, NavigationMenuLink, NavigationMenuList } from "@/components/ui/navigation-menu"

export function Navbar() {
    return (
        <div className="w-full border-b">
            <div className="flex h-16 items-center px-4">
                <NavigationMenu className="w-full">
                    <NavigationMenuList className="w-full">
                        <NavigationMenuItem className="w-full">
                            <NavigationMenuLink className="text-lg font-semibold w-full">
                                Bank Reconciliation
                            </NavigationMenuLink>
                        </NavigationMenuItem>
                    </NavigationMenuList>
                </NavigationMenu>
            </div>
        </div>
    )
} 