import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import ipaddress
import csv

class SubnetVisualizer:
    def __init__(self, master):
        self.master = master
        master.title("Subnet Visualizer")

        # Summary Address
        self.summary_frame = tk.Frame(master)
        self.summary_frame.pack(pady=10)

        tk.Label(self.summary_frame, text="Summary Address:").pack(side=tk.LEFT)
        self.summary_entry = tk.Entry(self.summary_frame)
        self.summary_entry.pack(side=tk.LEFT, padx=5)
        self.summary_entry.bind("<FocusOut>", self.update_summary_range)

        self.summary_range_label = tk.Label(self.summary_frame, text="")
        self.summary_range_label.pack(side=tk.LEFT, padx=5)

        # Add Subnet
        self.add_subnet_frame = tk.Frame(master)
        self.add_subnet_frame.pack()

        tk.Label(self.add_subnet_frame, text="Subnet Label:").pack(side=tk.LEFT)
        self.subnet_label_entry = tk.Entry(self.add_subnet_frame)
        self.subnet_label_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(self.add_subnet_frame, text="Subnet:").pack(side=tk.LEFT)
        self.subnet_entry = tk.Entry(self.add_subnet_frame)
        self.subnet_entry.pack(side=tk.LEFT, padx=5)

        self.add_subnet_button = tk.Button(self.add_subnet_frame, text="Add Subnet", command=self.add_subnet)
        self.add_subnet_button.pack(side=tk.LEFT, padx=5)

        # Import and Export Buttons
        button_frame = tk.Frame(master)
        button_frame.pack(pady=5)

        self.import_button = tk.Button(button_frame, text="Import from CSV", command=self.import_from_csv)
        self.import_button.pack(side=tk.LEFT, padx=5)

        self.export_button = tk.Button(button_frame, text="Export to CSV", command=self.export_to_csv)
        self.export_button.pack(side=tk.LEFT, padx=5)

        # --- Canvas and Scrollbars ---
        self.canvas_frame = tk.Frame(master)
        self.canvas_frame.pack(pady=20, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, bg="lightgray", scrollregion=(0, 0, 800, 600))
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.y_scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=self.y_scrollbar.set)

        # Subnet List
        self.subnets = []

        # Drag and resize variables
        self.selected_subnet = None
        self.drag_data = {"x": 0, "y": 0, "item": None, "resize": None}

        # Bind events
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.canvas.bind("<MouseWheel>", self.on_canvas_scroll)

        # --- Virtual Canvas Frame (for drawing) ---
        self.visual_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.visual_frame, anchor="nw")

    def update_summary_range(self, event=None):
        summary_address_str = self.summary_entry.get()
        if not summary_address_str:
            self.summary_range_label.config(text="")
            return

        try:
            summary_network = ipaddress.ip_network(summary_address_str, strict=False)
            first_ip = summary_network[1]
            last_ip = summary_network[-2]
            self.summary_range_label.config(text=f"({first_ip} - {last_ip})")
        except ValueError:
            self.summary_range_label.config(text="(Invalid Summary Address)")

    def add_subnet(self):
        summary_address_str = self.summary_entry.get()
        subnet_label = self.subnet_label_entry.get()
        subnet_str = self.subnet_entry.get()

        try:
            summary_network = ipaddress.ip_network(summary_address_str, strict=False)
            subnet = ipaddress.ip_network(subnet_str, strict=False)
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid IP address or subnet: {e}")
            return

        if not summary_network.supernet_of(subnet):
            messagebox.showerror("Error", "Subnet is not within the summary address range.")
            return

        for existing_subnet in self.subnets:
            if existing_subnet['network'].overlaps(subnet):
                messagebox.showerror("Error", f"Subnet overlaps with existing subnet: {existing_subnet['label']}")
                return

        self.subnets.append({
            'label': subnet_label,
            'network': subnet,
            'rect_id': None,
            'label_id': None
        })

        self.subnets.sort(key=lambda x: x['network'].network_address)
        self.subnet_label_entry.delete(0, tk.END)
        self.subnet_entry.delete(0, tk.END)
        self.visualize_subnets(summary_network)

    def import_from_csv(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filepath:
            return

        try:
            with open(filepath, "r") as csvfile:
                reader = csv.DictReader(csvfile)

                if not self.summary_entry.get():
                    first_row = next(reader)
                    first_subnet = ipaddress.ip_network(first_row["Subnet"], strict=False)
                    summary_network = first_subnet.supernet(prefixlen_diff=1)

                    self.summary_entry.insert(0, str(summary_network))
                    csvfile.seek(0)
                    next(reader)

                for row in reader:
                    subnet = ipaddress.ip_network(row["Subnet"], strict=False)
                    self.subnets.append({
                        'label': row["Label"],
                        'network': subnet,
                        'rect_id': None,
                        'label_id': None
                    })

            self.subnets.sort(key=lambda x: x['network'].network_address)
            summary_network = ipaddress.ip_network(self.summary_entry.get(), strict=False)
            self.visualize_subnets(summary_network)

        except Exception as e:
            messagebox.showerror("Import Error", f"An error occurred: {e}")

    def visualize_subnets(self, summary_network):
        # Clear the visual_frame instead of the canvas
        for widget in self.visual_frame.winfo_children():
            widget.destroy()

        self.canvas.delete("all")

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        summary_bar_height = 30

        # Summary address range text
        first_ip = summary_network[1]
        last_ip = summary_network[-2]
        summary_range_text = f"{summary_network} ({first_ip} - {last_ip})"

        self.canvas.create_rectangle(0, 0, canvas_width, summary_bar_height, fill="blue", outline="black")
        self.canvas.create_text(10, summary_bar_height / 2, text=summary_range_text, anchor=tk.W, fill="white")

        total_addresses = summary_network.num_addresses
        start_y = summary_bar_height + 10
        current_address = summary_network.network_address

        for subnet in self.subnets:
            # Draw space between subnets if any
            if current_address < subnet['network'].network_address:
                gap_addresses = int(subnet['network'].network_address) - int(current_address)
                gap_ratio = gap_addresses / total_addresses
                gap_height = max((canvas_height - start_y - 20) * gap_ratio, 0)

                # Calculate first and last IP of the gap
                first_gap_ip = current_address
                last_gap_ip = subnet['network'].network_address - 1
                gap_range_text = f"Available ({first_gap_ip} - {last_gap_ip})"

                gap_id = self.canvas.create_rectangle(10, start_y, canvas_width - 10, start_y + gap_height, fill="gray", outline="black")
                self.canvas.create_text(20, start_y + gap_height / 2, text=gap_range_text, anchor=tk.W, fill="black")
                self.canvas.itemconfig(gap_id, tags=("gap",))

                start_y += gap_height + 5

            # Draw subnet
            subnet_ratio = subnet['network'].num_addresses / total_addresses
            subnet_height = max((canvas_height - start_y - 20) * subnet_ratio, 20)

            rect_id = self.canvas.create_rectangle(10, start_y, canvas_width - 10, start_y + subnet_height, fill="green", outline="black")
            label_text = f"{subnet['label']} ({subnet['network']})"
            label_id = self.canvas.create_text(20, start_y + subnet_height / 2, text=label_text, anchor=tk.W, fill="white")

            subnet['rect_id'] = rect_id
            subnet['label_id'] = label_id
            self.canvas.itemconfig(rect_id, tags=("subnet", subnet['label']))

            start_y += subnet_height + 5
            current_address = subnet['network'].broadcast_address + 1

        # Draw remaining space at the end
        if current_address < summary_network.broadcast_address:
            remaining_addresses = int(summary_network.broadcast_address) - int(current_address) + 1
            remaining_ratio = remaining_addresses / total_addresses
            remaining_height = max((canvas_height - start_y - 10) * remaining_ratio, 0)

            # Calculate first and last IP of the remaining space
            first_remaining_ip = current_address
            last_remaining_ip = summary_network.broadcast_address
            remaining_range_text = f"Available ({first_remaining_ip} - {last_remaining_ip})"

            remaining_id = self.canvas.create_rectangle(10, start_y, canvas_width - 10, start_y + remaining_height, fill="gray", outline="black")
            self.canvas.create_text(20, start_y + remaining_height / 2, text=remaining_range_text, anchor=tk.W, fill="black")
            self.canvas.itemconfig(remaining_id, tags=("gap",))

        # Update scroll region after drawing
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def export_to_csv(self):
        if not self.subnets:
            messagebox.showwarning("Warning", "No subnets to export.")
            return

        try:
            with open("subnets.csv", "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Label", "Subnet", "Network Address", "Broadcast Address", "Number of Hosts"])

                for subnet in self.subnets:
                    writer.writerow([
                        subnet['label'],
                        str(subnet['network']),
                        str(subnet['network'].network_address),
                        str(subnet['network'].broadcast_address),
                        subnet['network'].num_addresses - 2
                    ])

            messagebox.showinfo("Export Successful", "Subnet data exported to subnets.csv")

        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred during export: {e}")

    def on_canvas_press(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        canvas_item = self.canvas.find_closest(x, y)
        tags = self.canvas.gettags(canvas_item)

        if "subnet" in tags:
            label = tags[1]
            self.selected_subnet = next((s for s in self.subnets if s['label'] == label), None)
            if self.selected_subnet:
                self.drag_data["item"] = self.selected_subnet['rect_id']
                self.drag_data["x"] = x
                self.drag_data["y"] = y
                rect_coords = self.canvas.coords(self.selected_subnet['rect_id'])

                if abs(y - rect_coords[3]) < 5:
                    self.drag_data["resize"] = "bottom"
                else:
                    self.drag_data["resize"] = None

    def on_canvas_drag(self, event):
        if self.selected_subnet and self.drag_data["item"]:
            x = self.canvas.canvasx(event.x)
            y = self.canvas.canvasy(event.y)

            if self.drag_data["resize"] == "bottom":
                rect_coords = self.canvas.coords(self.drag_data["item"])
                new_height = y - rect_coords[1]
                if new_height > 20:
                    self.canvas.coords(self.drag_data["item"], rect_coords[0], rect_coords[1], rect_coords[2], y)

                    label_id = self.selected_subnet['label_id']
                    self.canvas.coords(label_id, 20, rect_coords[1] + new_height / 2)
            else:
                delta_x = x - self.drag_data["x"]
                delta_y = y - self.drag_data["y"]
                self.canvas.move(self.drag_data["item"], 0, delta_y)

                label_id = self.selected_subnet['label_id']
                self.canvas.move(label_id, 0, delta_y)

                self.drag_data["x"] = x
                self.drag_data["y"] = y

    def on_canvas_release(self, event):
        if self.selected_subnet and self.drag_data["item"]:
            if self.drag_data["resize"] == "bottom":
                # Update subnet size
                rect_coords = self.canvas.coords(self.selected_subnet['rect_id'])
                start_y = rect_coords[1]
                end_y = rect_coords[3]

                canvas_height = self.canvas.winfo_height()
                summary_network = ipaddress.ip_network(self.summary_entry.get(), strict=False)
                total_addresses = summary_network.num_addresses
                new_subnet_height = end_y - start_y
                new_subnet_ratio = new_subnet_height / (canvas_height - 40)
                new_num_addresses = int(total_addresses * new_subnet_ratio)

                new_prefix_length = int(32 - (new_num_addresses - 1).bit_length())

                self.selected_subnet['network'] = ipaddress.ip_network(f"{self.selected_subnet['network'].network_address}/{new_prefix_length}", strict=False)
                self.subnets.sort(key=lambda x: x['network'].network_address)
                self.visualize_subnets(summary_network)
            else:
                # Move subnet
                rect_coords = self.canvas.coords(self.selected_subnet['rect_id'])
                start_y = rect_coords[1]

                canvas_height = self.canvas.winfo_height()
                summary_network = ipaddress.ip_network(self.summary_entry.get(), strict=False)
                total_addresses = summary_network.num_addresses
                new_position_ratio = (start_y - 40) / (canvas_height - 40)
                new_subnet_address_int = int(summary_network.network_address) + int(total_addresses * new_position_ratio)
                new_subnet_address = ipaddress.ip_address(new_subnet_address_int)

                self.selected_subnet['network'] = ipaddress.ip_network(f"{new_subnet_address}/{self.selected_subnet['network'].prefixlen}", strict=False)

                # Check for overlaps and revert if necessary
                temp_subnets = self.subnets[:]
                self.subnets.sort(key=lambda x: x['network'].network_address)
                for i, subnet in enumerate(self.subnets):
                    if i > 0 and subnet['network'].overlaps(self.subnets[i - 1]['network']):
                        messagebox.showerror("Error", "Subnet move causes overlap. Reverting.")
                        self.subnets = temp_subnets
                        break

                self.visualize_subnets(summary_network)

            self.selected_subnet = None
            self.drag_data["item"] = None
            self.drag_data["resize"] = None

    def on_canvas_double_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        canvas_item = self.canvas.find_closest(x, y)
        tags = self.canvas.gettags(canvas_item)

        if "subnet" in tags:
            label = tags[1]
            subnet_to_edit = next((s for s in self.subnets if s['label'] == label), None)
            if subnet_to_edit:
                self.edit_subnet(subnet_to_edit)

    def edit_subnet(self, subnet):
        edit_window = tk.Toplevel(self.master)
        edit_window.title("Edit Subnet")

        tk.Label(edit_window, text="Label:").grid(row=0, column=0, padx=5, pady=5)
        label_entry = tk.Entry(edit_window)
        label_entry.insert(0, subnet['label'])
        label_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(edit_window, text="Network (CIDR):").grid(row=1, column=0, padx=5, pady=5)
        network_entry = tk.Entry(edit_window)
        network_entry.insert(0, str(subnet['network']))
        network_entry.grid(row=1, column=1, padx=5, pady=5)

        def save_changes():
            new_label = label_entry.get()
            new_network_str = network_entry.get()

            try:
                new_network = ipaddress.ip_network(new_network_str, strict=False)
            except ValueError:
                messagebox.showerror("Error", "Invalid subnet address.")
                return

            for existing_subnet in self.subnets:
                if existing_subnet is not subnet and existing_subnet['network'].overlaps(new_network):
                    messagebox.showerror("Error", f"Subnet overlaps with existing subnet: {existing_subnet['label']}")
                    return

            subnet['label'] = new_label
            subnet['network'] = new_network

            self.canvas.itemconfig(subnet['rect_id'], tags=("subnet", new_label))

            self.subnets.sort(key=lambda x: x['network'].network_address)
            self.visualize_subnets(ipaddress.ip_network(self.summary_entry.get(), strict=False))
            edit_window.destroy()

        save_button = tk.Button(edit_window, text="Save Changes", command=save_changes)
        save_button.grid(row=2, column=0, columnspan=2, pady=10)

    def on_canvas_resize(self, event):
        if self.summary_entry.get():
            summary_network = ipaddress.ip_network(self.summary_entry.get(), strict=False)
            self.visualize_subnets(summary_network)

    def on_canvas_scroll(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

root = tk.Tk()
app = SubnetVisualizer(root)
root.mainloop()